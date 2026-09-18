from __future__ import annotations

# v2.4 registry: union of v1 engine modules + v2 adapters (no feature loss)

from app.modules.ebooks import EbooksModule
from app.modules.youtube import YouTubeModule
from app.modules.etsy import EtsyModule
from app.modules.newsletter import NewsletterModule
from app.modules.affiliate import AffiliateModule
from app.modules.pod import PrintOnDemandModule
from app.modules.stock import StockMediaModule

from app.modules.templates import TemplatePacksModule
from app.modules.microcourse import MicroCourseModule
from app.modules.licensing import LicensingPackModule
from app.modules.leadmagnet import LeadMagnetModule
from app.modules.directory import DirectoryProductModule
from app.modules.community import CommunityPlaybookModule

from app.modules.marketplace_assets import MarketplaceAssetsModule
from app.modules.miniapp import MiniAppProductizerModule
from app.modules.extension import BrowserExtensionModule

from app.modules.trend_miner import TrendMinerModule
from app.modules.repurposer import RepurposerModule
from app.modules.offer_ladder import OfferLadderModule
from app.modules.conversion_packager import ConversionPackagerModule
from app.modules.pricing_optimizer import PricingOptimizerModule
from app.modules.review_miner import ReviewMinerModule
from app.modules.support_macros import SupportMacrosModule

from app.modules.calendar_generator import CalendarGeneratorModule
from app.modules.brandkit_cover_factory import BrandKitCoverFactoryModule
from app.modules.metrics_optimizer import MetricsOptimizerModule

from app.modules.offer_qa_gate import OfferQAGateModule
from app.modules.ab_kit_generator import ABKitGeneratorModule
from app.modules.inbox_faq_builder import InboxFAQBuilderModule
from app.modules.terms_generator import TermsGeneratorModule

from app.modules.platform_packs import PlatformPacksModule
from app.modules.seo_engine import SEOEngineModule
from app.modules.funnel_engine import FunnelEngineModule
from app.modules.personalization_engine import PersonalizationEngineModule

from app.modules.creative_factory import CreativeFactoryModule
from app.modules.localization_engine import LocalizationEngineModule
from app.modules.experiment_runner import ExperimentRunnerModule
from app.modules.personalization_runner import PersonalizationRunnerModule
from app.modules.programmatic_seo_generator import ProgrammaticSEOGeneratorModule
from app.modules.pod_pack_generator import PODPackGeneratorModule
from app.modules.licensing_stamper import LicensingStamperModule

from app.modules.membership_automation import MembershipAutomationModule
from app.modules.ecosystem_template_packs import EcosystemTemplatePacksModule
from app.modules.affiliate_site_mode import AffiliateSiteModeModule
from app.modules.micro_tool_generator import MicroToolGeneratorModule
from app.modules.marketplace_listing_optimizer import MarketplaceListingOptimizerModule
from app.modules.affiliate_tables_generator import AffiliateTablesGeneratorModule
from app.modules.affiliate_comparison_scale import AffiliateComparisonScaleModule
from app.modules.membership_issue_generator import MembershipIssueGeneratorModule
from app.modules.pod_superpack import PODSuperPackModule
from app.modules.bundle_assembler import BundleAssemblerModule

from app.modules.licensing_matrix_generator import LicensingMatrixGeneratorModule
from app.modules.storefront_html_generator import StorefrontHTMLGeneratorModule
from app.modules.storefront_site_builder import StorefrontSiteBuilderModule
from app.modules.onboarding_automation import OnboardingAutomationModule
from app.modules.dataset_to_product_pipeline import DatasetToProductPipelineModule
from app.modules.support_refund_autopack import SupportRefundAutoPackModule

# v1.5+ additions (native v1 engine modules)
from app.modules.price_testing_simulator import PriceTestingSimulatorModule
from app.modules.seo_site_compiler import SEOSiteCompilerModule

# v1.6 additions ported to v1 engine style
from app.modules.programmatic_seo_369 import ProgrammaticSEO369Module
from app.modules.variant_factory_loops import VariantFactoryLoopsModule

# v2.x additions (wrapped adapters calling app.modules_v2.* implementations)
from app.modules.analytics_import_normalizer import AnalyticsImportNormalizerModule
from app.modules.bundle_upsell_engine import BundleUpsellEngineModule
from app.modules.collaboration_case_study_generator import CollaborationCaseStudyGeneratorModule
from app.modules.funnel_compiler import FunnelCompilerModule
from app.modules.journal_workbook_generator import JournalWorkbookGeneratorModule
from app.modules.landing_finalizer import LandingFinalizerModule
from app.modules.lead_magnet_funnel_builder import LeadMagnetFunnelBuilderModule
from app.modules.lead_magnet_snippet import LeadMagnetSnippetModule
from app.modules.membership_drip_calendar import MembershipDripCalendarModule
from app.modules.newsletter_excerpt import NewsletterExcerptModule
from app.modules.pricing_listing_variant_runner import PricingListingVariantRunnerModule
from app.modules.product_bundle_generator import ProductBundleGeneratorModule
from app.modules.prompt_library_generator import PromptLibraryGeneratorModule
from app.modules.repurposing_scheduler import RepurposingSchedulerModule
from app.modules.seo_site_publisher import SeoSitePublisherModule
from app.modules.sku_library_compiler import SkuLibraryCompilerModule
from app.modules.social_posts import SocialPostsModule
from app.modules.testimonial_collector import TestimonialCollectorModule
from app.modules.vault_generator import VaultGeneratorModule
from app.modules.workshop_webinar_kit import WorkshopWebinarKitModule
from app.modules.youtube_script import YoutubeScriptModule
from app.modules.career_tools import CareerToolsModule
from app.modules.podcast_script_generator import PodcastScriptGeneratorModule
from app.modules.presentation_generator import PresentationGeneratorModule
from app.modules.infographic_generator import InfographicGeneratorModule
from app.modules.study_module import StudyModuleModule
from app.modules.audio_generator import AudioGeneratorModule
from app.modules.video_generator import VideoGeneratorModule
from app.modules.hooks_generator import HooksGeneratorModule
from app.modules.product_packager import ProductPackagerModule
from app.modules.sales_copy_generator import SalesCopyGeneratorModule
from app.modules.distribution_generator import DistributionGeneratorModule
from app.modules.content_exporter import ContentExporterModule
from app.modules.publish_controller import PublishControllerModule
from app.modules.gumroad_publisher import GumroadPublisherModule
from app.modules.youtube_publisher import YoutubePublisherModule
from app.modules.newsletter_packager import NewsletterPackagerModule
from app.modules.social_launch_packager import SocialLaunchPackagerModule
from app.modules.payhip_packager import PayhipPackagerModule
from app.modules.image_generator_v2 import ImageGeneratorV2Module
from app.modules.prediction_tracker import PredictionTrackerModule
from app.modules.trend_surfer import TrendSurferModule
from app.modules.idea_miner import IdeaMinerModule
from app.modules.sales_page_builder import SalesPageBuilderModule
from app.modules.email_sequence_builder import EmailSequenceBuilderModule
from app.modules.cross_pollinator import CrossPollinatorModule
from app.modules.thread_bomber import ThreadBomberModule
from app.modules.short_form_pack import ShortFormPackModule
from app.modules.competitor_dissector import CompetitorDissectorModule
from app.modules.vault_auditor import VaultAuditorModule
from app.modules.comfyui_director import ComfyUIDirectorModule
from app.modules.thumbnail_generator import ThumbnailGeneratorModule
from app.modules.product_cover_generator import ProductCoverGeneratorModule
from app.modules.social_visual_generator import SocialVisualGeneratorModule
from app.modules.visual_ranker import VisualRankerModule


REGISTRY = {
    # Core lanes
    "ebooks": EbooksModule(),
    "youtube": YouTubeModule(),
    "etsy": EtsyModule(),
    "newsletter": NewsletterModule(),
    "affiliate": AffiliateModule(),
    "pod": PrintOnDemandModule(),
    "stock": StockMediaModule(),

    # Digital product lanes
    "templates": TemplatePacksModule(),
    "microcourse": MicroCourseModule(),
    "licensing": LicensingPackModule(),
    "leadmagnet": LeadMagnetModule(),
    "directory": DirectoryProductModule(),
    "community": CommunityPlaybookModule(),

    # Marketplace / software lanes
    "marketplace_assets": MarketplaceAssetsModule(),
    "miniapp": MiniAppProductizerModule(),
    "extension": BrowserExtensionModule(),

    # Meta automation layers
    "trend_miner": TrendMinerModule(),
    "repurposer": RepurposerModule(),
    "offer_ladder": OfferLadderModule(),
    "conversion_packager": ConversionPackagerModule(),
    "pricing_optimizer": PricingOptimizerModule(),
    "review_miner": ReviewMinerModule(),
    "support_macros": SupportMacrosModule(),

    # Calendar + branding + metrics
    "calendar_generator": CalendarGeneratorModule(),
    "brandkit_cover_factory": BrandKitCoverFactoryModule(),
    "metrics_optimizer": MetricsOptimizerModule(),

    # QA + experiments + support-to-FAQ + legal terms
    "offer_qa_gate": OfferQAGateModule(),
    "ab_kit_generator": ABKitGeneratorModule(),
    "inbox_faq_builder": InboxFAQBuilderModule(),
    "terms_generator": TermsGeneratorModule(),

    # Universalization: platform packs + SEO + funnels + personalization
    "platform_packs": PlatformPacksModule(),
    "seo_engine": SEOEngineModule(),
    "funnel_engine": FunnelEngineModule(),
    "personalization_engine": PersonalizationEngineModule(),

    # Creative + localization + experiments + personalization runner
    "creative_factory": CreativeFactoryModule(),
    "localization_engine": LocalizationEngineModule(),
    "experiment_runner": ExperimentRunnerModule(),
    "personalization_runner": PersonalizationRunnerModule(),

    # Programmatic SEO + POD packs + stamping
    "programmatic_seo_generator": ProgrammaticSEOGeneratorModule(),
    "pod_pack_generator": PODPackGeneratorModule(),
    "licensing_stamper": LicensingStamperModule(),

    # Membership + ecosystem templates + affiliate site + micro tools + listing optimizer
    "membership_automation": MembershipAutomationModule(),
    "ecosystem_template_packs": EcosystemTemplatePacksModule(),
    "affiliate_site_mode": AffiliateSiteModeModule(),
    "micro_tool_generator": MicroToolGeneratorModule(),
    "marketplace_listing_optimizer": MarketplaceListingOptimizerModule(),

    # Affiliate tables + membership issues + POD superpack + 9-SKU assembler
    "affiliate_tables_generator": AffiliateTablesGeneratorModule(),
    "affiliate_comparison_scale": AffiliateComparisonScaleModule(),
    "membership_issue_generator": MembershipIssueGeneratorModule(),
    "pod_superpack": PODSuperPackModule(),
    "bundle_assembler": BundleAssemblerModule(),

    # Licensing matrix + storefront + onboarding + dataset->product + support/refund
    "licensing_matrix_generator": LicensingMatrixGeneratorModule(),
    "storefront_html_generator": StorefrontHTMLGeneratorModule(),
    "storefront_site_builder": StorefrontSiteBuilderModule(),
    "onboarding_automation": OnboardingAutomationModule(),
    "dataset_to_product_pipeline": DatasetToProductPipelineModule(),
    "support_refund_autopack": SupportRefundAutoPackModule(),

    # v1.5+ extras
    "price_testing_simulator": PriceTestingSimulatorModule(),
    "seo_site_compiler": SEOSiteCompilerModule(),

    # v1.6+ extras
    "programmatic_seo_369": ProgrammaticSEO369Module(),
    "variant_factory_loops": VariantFactoryLoopsModule(),

    # v2.x adapters (no feature loss)
    "analytics_import_normalizer": AnalyticsImportNormalizerModule(),
    "bundle_upsell_engine": BundleUpsellEngineModule(),
    "collaboration_case_study_generator": CollaborationCaseStudyGeneratorModule(),
    "funnel_compiler": FunnelCompilerModule(),
    "journal_workbook_generator": JournalWorkbookGeneratorModule(),
    "landing_finalizer": LandingFinalizerModule(),
    "lead_magnet_funnel_builder": LeadMagnetFunnelBuilderModule(),
    "lead_magnet_snippet": LeadMagnetSnippetModule(),
    "membership_drip_calendar": MembershipDripCalendarModule(),
    "newsletter_excerpt": NewsletterExcerptModule(),
    "pricing_listing_variant_runner": PricingListingVariantRunnerModule(),
    "product_bundle_generator": ProductBundleGeneratorModule(),
    "prompt_library_generator": PromptLibraryGeneratorModule(),
    "repurposing_scheduler": RepurposingSchedulerModule(),
    "seo_site_publisher": SeoSitePublisherModule(),
    "sku_library_compiler": SkuLibraryCompilerModule(),
    "social_posts": SocialPostsModule(),
    "testimonial_collector": TestimonialCollectorModule(),
    "vault_generator": VaultGeneratorModule(),
    "workshop_webinar_kit": WorkshopWebinarKitModule(),
    "youtube_script": YoutubeScriptModule(),
    "podcast_script_generator": PodcastScriptGeneratorModule(),
    "presentation_generator": PresentationGeneratorModule(),
    "infographic_generator": InfographicGeneratorModule(),
    "study_module": StudyModuleModule(),
    "audio_generator": AudioGeneratorModule(),
    "video_generator": VideoGeneratorModule(),
    "hooks_generator": HooksGeneratorModule(),
    "product_packager": ProductPackagerModule(),
    "sales_copy_generator": SalesCopyGeneratorModule(),
    "distribution_generator": DistributionGeneratorModule(),
    "content_exporter": ContentExporterModule(),
    "publish_controller": PublishControllerModule(),
    "gumroad_publisher": GumroadPublisherModule(),
    "youtube_publisher": YoutubePublisherModule(),
    "newsletter_packager": NewsletterPackagerModule(),
    "social_launch_packager": SocialLaunchPackagerModule(),
    "payhip_packager": PayhipPackagerModule(),
    "image_generator_v2": ImageGeneratorV2Module(),
    "prediction_tracker": PredictionTrackerModule(),
    "trend_surfer": TrendSurferModule(),
    "idea_miner": IdeaMinerModule(),
    "sales_page_builder": SalesPageBuilderModule(),
    "email_sequence_builder": EmailSequenceBuilderModule(),
    "cross_pollinator": CrossPollinatorModule(),
    "thread_bomber": ThreadBomberModule(),
    "short_form_pack": ShortFormPackModule(),
    "competitor_dissector": CompetitorDissectorModule(),
    "vault_auditor": VaultAuditorModule(),
    "comfyui_director": ComfyUIDirectorModule(),
    "thumbnail_generator": ThumbnailGeneratorModule(),
    "product_cover_generator": ProductCoverGeneratorModule(),
    "social_visual_generator": SocialVisualGeneratorModule(),
    "visual_ranker": VisualRankerModule(),

    # v4.0 - Career & Job Search Tools
    "career_tools": CareerToolsModule(),
}
