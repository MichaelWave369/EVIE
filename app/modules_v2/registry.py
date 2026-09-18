from __future__ import annotations
from .base import Module

# Core flywheel modules
from . import offer_ladder, funnel_engine, conversion_packager, seo_engine, programmatic_seo_generator
from . import affiliate_tables_generator, pod_superpack, creative_factory, localization_engine
from . import storefront_html_generator, storefront_site_builder
from . import marketplace_listing_optimizer
from . import platform_packs, landing_finalizer, funnel_compiler, licensing_matrix_generator, support_refund_autopack, product_bundle_generator, seo_site_publisher

# Passive income expansion modules (v1.9)
from . import prompt_library_generator, vault_generator, workshop_webinar_kit, journal_workbook_generator
from . import bundle_upsell_engine, testimonial_collector, analytics_import_normalizer
from . import repurposer, repurposing_scheduler
from . import newsletter_excerpt, youtube_script, social_posts, lead_magnet_snippet, lead_magnet_funnel_builder
from . import collaboration_case_study_generator, membership_drip_calendar, sku_library_compiler, pricing_listing_variant_runner
from . import thumbnail_generator, product_cover_generator, social_visual_generator, visual_ranker
from . import prediction_tracker, trend_surfer, idea_miner, sales_page_builder, email_sequence_builder, cross_pollinator
from . import thread_bomber, short_form_pack, competitor_dissector, vault_auditor, comfyui_director

_MODULES: dict[str, Module] = {
    # Existing chain
    offer_ladder.OfferLadder.name: offer_ladder.OfferLadder(),
    funnel_engine.FunnelEngine.name: funnel_engine.FunnelEngine(),
    conversion_packager.ConversionPackager.name: conversion_packager.ConversionPackager(),
    seo_engine.SEOEngine.name: seo_engine.SEOEngine(),
    programmatic_seo_generator.ProgrammaticSEOGenerator.name: programmatic_seo_generator.ProgrammaticSEOGenerator(),
    affiliate_tables_generator.AffiliateTablesGenerator.name: affiliate_tables_generator.AffiliateTablesGenerator(),
    pod_superpack.PODSuperpack.name: pod_superpack.PODSuperpack(),
    creative_factory.CreativeFactory.name: creative_factory.CreativeFactory(),
    localization_engine.LocalizationEngine.name: localization_engine.LocalizationEngine(),
    marketplace_listing_optimizer.MarketplaceListingOptimizer.name: marketplace_listing_optimizer.MarketplaceListingOptimizer(),
    storefront_html_generator.StorefrontHTMLGenerator.name: storefront_html_generator.StorefrontHTMLGenerator(),
    storefront_site_builder.StorefrontSiteBuilder.name: storefront_site_builder.StorefrontSiteBuilder(),
    platform_packs.PlatformPacks.name: platform_packs.PlatformPacks(),
    landing_finalizer.LandingFinalizer.name: landing_finalizer.LandingFinalizer(),
    funnel_compiler.FunnelCompiler.name: funnel_compiler.FunnelCompiler(),
    licensing_matrix_generator.LicensingMatrixGenerator.name: licensing_matrix_generator.LicensingMatrixGenerator(),
    support_refund_autopack.SupportRefundAutopack.name: support_refund_autopack.SupportRefundAutopack(),
    seo_site_publisher.SEOSitePublisher.name: seo_site_publisher.SEOSitePublisher(),
    product_bundle_generator.ProductBundleGenerator.name: product_bundle_generator.ProductBundleGenerator(),

    # New passive income modules
    prompt_library_generator.PromptLibraryGenerator.name: prompt_library_generator.PromptLibraryGenerator(),
    vault_generator.VaultGenerator.name: vault_generator.VaultGenerator(),
    workshop_webinar_kit.WorkshopWebinarKit.name: workshop_webinar_kit.WorkshopWebinarKit(),
    journal_workbook_generator.JournalWorkbookGenerator.name: journal_workbook_generator.JournalWorkbookGenerator(),
    bundle_upsell_engine.BundleUpsellEngine.name: bundle_upsell_engine.BundleUpsellEngine(),
    testimonial_collector.TestimonialCollector.name: testimonial_collector.TestimonialCollector(),
    analytics_import_normalizer.AnalyticsImportNormalizer.name: analytics_import_normalizer.AnalyticsImportNormalizer(),
    repurposer.Repurposer.name: repurposer.Repurposer(),
    repurposing_scheduler.RepurposingScheduler.name: repurposing_scheduler.RepurposingScheduler(),
    newsletter_excerpt.NewsletterExcerpt.name: newsletter_excerpt.NewsletterExcerpt(),
    youtube_script.YouTubeScript.name: youtube_script.YouTubeScript(),
    social_posts.SocialPosts.name: social_posts.SocialPosts(),
    lead_magnet_snippet.LeadMagnetSnippet.name: lead_magnet_snippet.LeadMagnetSnippet(),
    collaboration_case_study_generator.CollaborationCaseStudyGenerator.name: collaboration_case_study_generator.CollaborationCaseStudyGenerator(),
    membership_drip_calendar.MembershipDripCalendar.name: membership_drip_calendar.MembershipDripCalendar(),
    lead_magnet_funnel_builder.LeadMagnetFunnelBuilder.name: lead_magnet_funnel_builder.LeadMagnetFunnelBuilder(),
    sku_library_compiler.SKULibraryCompiler.name: sku_library_compiler.SKULibraryCompiler(),
    pricing_listing_variant_runner.PricingListingVariantRunner.name: pricing_listing_variant_runner.PricingListingVariantRunner(),
    thumbnail_generator.ThumbnailGenerator.name: thumbnail_generator.ThumbnailGenerator(),
    product_cover_generator.ProductCoverGenerator.name: product_cover_generator.ProductCoverGenerator(),
    social_visual_generator.SocialVisualGenerator.name: social_visual_generator.SocialVisualGenerator(),
    visual_ranker.VisualRanker.name: visual_ranker.VisualRanker(),
    prediction_tracker.PredictionTracker.name: prediction_tracker.PredictionTracker(),
    trend_surfer.TrendSurfer.name: trend_surfer.TrendSurfer(),
    idea_miner.IdeaMiner.name: idea_miner.IdeaMiner(),
    sales_page_builder.SalesPageBuilder.name: sales_page_builder.SalesPageBuilder(),
    email_sequence_builder.EmailSequenceBuilder.name: email_sequence_builder.EmailSequenceBuilder(),
    cross_pollinator.CrossPollinator.name: cross_pollinator.CrossPollinator(),
    thread_bomber.ThreadBomber.name: thread_bomber.ThreadBomber(),
    short_form_pack.ShortFormPack.name: short_form_pack.ShortFormPack(),
    competitor_dissector.CompetitorDissector.name: competitor_dissector.CompetitorDissector(),
    vault_auditor.VaultAuditor.name: vault_auditor.VaultAuditor(),
    comfyui_director.ComfyUIDirector.name: comfyui_director.ComfyUIDirector(),
}

def list_modules() -> list[str]:
    return sorted(_MODULES.keys())

def get_module(name: str):
    m = _MODULES.get(name)
    if not m:
        raise KeyError(f"Unknown module: {name}")
    return m
