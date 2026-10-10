"""R22 loopback service: no HTTP execution, token isolation and read-only policy."""
from __future__ import annotations

import http.client
import json
import os
import stat
import threading
from pathlib import Path

import pytest

from tools import evie_local_service as service
from tools import evie_safe
from tools import evie_governed_flow as flow

TOKEN="a"*64


@pytest.fixture
def live_server():
    server=service.LocalOnlyHTTPServer(0,TOKEN)
    thread=threading.Thread(target=server.serve_forever,kwargs={"poll_interval":0.01},daemon=True)
    thread.start()
    try:
        yield server,server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def request(port, method, path, *, token=TOKEN, headers=None, body=None):
    provided={} if headers is None else dict(headers)
    if token is not None:
        provided["Authorization"]="Bearer "+token
    connection=http.client.HTTPConnection(service.HOST,port,timeout=3)
    try:
        connection.request(method,path,headers=provided,body=body)
        response=connection.getresponse()
        data=response.read(50_000)
        return response.status,dict(response.getheaders()),(
            json.loads(data) if method!="HEAD" else {"executionAuthorized":False}
        )
    finally:
        connection.close()


def test_binds_exact_ipv4_loopback_only_and_has_no_software_executor(live_server,monkeypatch):
    server,port=live_server
    assert server.server_address[0]=="127.0.0.1"
    assert set(service.ROUTES)=={"/v1/health","/v1/policy","/v1/plan","/v1/security"}
    monkeypatch.setattr(flow,"start_session",lambda **kw: (_ for _ in ()).throw(AssertionError("remote execution should not occur")))
    monkeypatch.setattr(flow,"resume_session",lambda **kw: (_ for _ in ()).throw(AssertionError("remote resume should not occur")))
    for path in sorted(service.ROUTES):
        status,headers,body=request(port,"GET",path)
        assert status==200
        assert headers["Cache-Control"]=="no-store"
        assert headers["X-Content-Type-Options"]=="nosniff"
        assert "Access-Control-Allow-Origin" not in headers
        assert body["httpExecutionEndpointsEnabled"] is False
        assert body["publishingAuthorized"] is False
    assert request(port,"GET","/v1/plan")[2]["data"]["state"]=="plan_only"
    guarded=request(port,"GET","/v1/security")[2]["data"]
    assert guarded["status"]=="EXECUTION_GATE_CLOSED"
    assert guarded["executionAllowed"] is False
    assert guarded["promotionReady"] is False
    assert len(guarded["promotionRequirements"])==6


def test_no_token_wrong_token_and_origin_are_rejected(live_server):
    _,port=live_server
    assert request(port,"GET","/v1/health",token=None)[0]==401
    assert request(port,"GET","/v1/health",token="b"*64)[0]==401
    assert request(port,"GET","/v1/health",headers={"Origin":"https://evil.example"})[0]==403
    assert request(port,"GET","/v1/health",headers={"Referer":"http://127.0.0.1/sneaky"})[0]==403
    assert request(port,"GET","/v1/policy",headers={"Host":"localhost:"+str(port)})[0]==403
    assert request(port,"GET","/v1/policy",headers={"Host":"evil.test"})[0]==403


def test_mutating_http_methods_never_dispatch(live_server,monkeypatch):
    _,port=live_server
    monkeypatch.setattr(evie_safe,"dispatch",lambda args: (_ for _ in ()).throw(AssertionError("dispatch forbidden")))
    monkeypatch.setattr(flow,"resume_session",lambda **kw: (_ for _ in ()).throw(AssertionError("resume forbidden")))
    for method in ("POST","PUT","PATCH","DELETE","OPTIONS","HEAD","TRACE","CONNECT"):
        status,_,body=request(port,method,"/v1/plan",body=b"{}")
        assert status==405
        assert body["executionAuthorized"] is False


def test_unlisted_paths_query_params_and_execution_route_are_denied(live_server):
    _,port=live_server
    for path in ("/v1/plan?execute=1","/v1/plan/","/v1/start","/v1/resume",
                 "/v1/publish","/v1/audit?session=../secrets","/v1/../../etc/passwd"):
        assert request(port,"GET",path)[0]==404


def test_token_created_exclusively_outside_repo_and_not_leaked(tmp_path):
    target=tmp_path/"bearer.token"
    saved=service.new_token_file(str(target))
    assert saved==target
    assert target.is_file()
    raw=target.read_text().strip()
    assert service.TOKEN_PATTERN.fullmatch(raw)
    assert raw==service.load_token(str(target))
    if os.name=="posix":
        assert not (target.stat().st_mode & (stat.S_IRWXG|stat.S_IRWXO))
    with pytest.raises(ValueError,match="existing"):
        service.new_token_file(str(target))
    assert target.read_text().strip()==raw
    with pytest.raises(ValueError,match="outside checkout"):
        service.new_token_file(str(service.ROOT/"unsafe.token"))
    assert service.main(["token","--token-file",str(target)])==1


def test_existing_symlink_or_world_readable_token_denied(tmp_path):
    original=tmp_path/"token"
    original.write_text(TOKEN+"\n")
    other=tmp_path/"alias"
    other.symlink_to(original)
    with pytest.raises(ValueError):
        service.load_token(str(other))
    if os.name=="posix":
        os.chmod(original,0o644)
        with pytest.raises(ValueError,match="group/world"):
            service.load_token(str(original))


def test_missing_or_incorrect_auth_cannot_expose_policy(live_server):
    _,port=live_server
    _,_,denied=request(port,"GET","/v1/policy",token=None)
    assert "legacyRoutes" not in denied
    _,_,success=request(port,"GET","/v1/policy")
    assert len(success["data"]["legacyRoutes"])==6
    assert request(port,"GET","/v1/security",token=None)[0]==401


def test_probe_reads_all_three_without_state_mutation(live_server,tmp_path):
    _,port=live_server
    output=service.probe(port=port,token=TOKEN)
    assert output["status"]=="read_only_loopback_probe_passed"
    assert output["routeCount"]==4
    assert output["sourcePlanState"]=="plan_only"
    assert output["executionAuthorized"] is False
    assert list(tmp_path.iterdir())==[]


def test_parser_has_no_bind_flag_and_no_execution_commands():
    assert service.parser().parse_args(["serve","--token-file","x"]).port==8765
    for words in [
        ["serve","--bind","0.0.0.0","--token-file","x"],
        ["serve","--module","hooks_generator","--token-file","x"],
        ["run","hooks_generator"],["resume"],["execute"],["publish"],
        ["probe","--token-file","x","--url","https://other"],
    ]:
        with pytest.raises(SystemExit):
            service.parser().parse_args(words)
    with pytest.raises(ValueError):
        service.LocalOnlyHTTPServer(8765,"short")


def test_cli_probe_requires_valid_bearer_file(tmp_path,capsys):
    missing=tmp_path/"missing.token"
    assert service.main(["probe","--token-file",str(missing)])==1
    output=json.loads(capsys.readouterr().out)
    assert output["status"]=="rejected"
    assert output["executionAuthorized"] is False
    assert "token" not in str(output)
