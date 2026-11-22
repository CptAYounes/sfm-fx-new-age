"""Source-labeled defaults, not resolutions of the open policy decisions."""
from decimal import Decimal
from sfm_fx_new_age.contracts.analytics import ParameterDefinition,MutableSurface


def register_core_parameters(catalogues):
    definitions=[
        ParameterDefinition('feed.quote_max_age_seconds','BAR_AND_QUOTE_CACHE','integer','seconds',minimum=Decimal(1),maximum=Decimal(3600),default=30),
        ParameterDefinition('scanner.pivot_left','STRATEGY_RECIPE_HOST','integer','completed_bars',minimum=Decimal(1),maximum=Decimal(20),default=2),
        ParameterDefinition('scanner.pivot_right','STRATEGY_RECIPE_HOST','integer','completed_bars',minimum=Decimal(1),maximum=Decimal(20),default=2)]
    for i,value in enumerate(('0.375','0.750','1.250','1.750','2.250')):
        definitions.append(ParameterDefinition(f'geometry.band_{i}','STRATEGY_RECIPE_HOST','number','ATR_MULTIPLE',minimum=Decimal('0.0001'),maximum=Decimal(20),default=value))
    for definition in definitions:catalogues.register_parameter(definition)
    for surface,keys,subtab,owner in [
        ('feed.freshness',('feed.quote_max_age_seconds',),'2.4','BAR_AND_QUOTE_CACHE'),
        ('scanner.research_pivots',('scanner.pivot_left','scanner.pivot_right'),'3.5','STRATEGY_RECIPE_HOST'),
        ('geometry.research_bands',tuple(f'geometry.band_{i}' for i in range(5)),'3.8','STRATEGY_RECIPE_HOST')]:
        catalogues.register_surface(MutableSurface(surface,owner,keys,subtab))
