from . import models


def post_init_hook(env):
    """Backfill threshold to average cost for existing products."""
    templates = env["product.template"].with_context(active_test=False).search(
        [("flewstack_threshold", "=", False)]
    )
    for tmpl in templates:
        variant = tmpl.product_variant_ids[:1]
        tmpl.flewstack_threshold = variant.standard_price if variant else 0.0
