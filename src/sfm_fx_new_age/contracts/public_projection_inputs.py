"""Pure projection input states. Missing evidence is not an empty market setup."""
class ProjectionInputUnavailable(Exception):
    def __init__(self,reason,state='DATA_UNAVAILABLE'):
        super().__init__(reason)
        self.reason=reason
        self.state=state


def optional_projection_source(key,kind,evidence,frame=None):
    """One source selector shared by calculations and cache/expiry identity."""
    source=evidence.get(kind)
    weekly=evidence.get('EXECUTED_WEEK_QUANTITIES') if frame=='W1' else None
    if key in {'volume_displacement','effort_result'} and weekly and (not source or source['provider_id']==weekly['provider_id']):return weekly
    quantities=evidence.get('EXECUTED_BAR_QUANTITIES')
    if key in {'volume_displacement','effort_result'} and quantities and (not source or source['provider_id']==quantities['provider_id']):
        return quantities
    # The controlling DOM_BOOK requirement permits genuine broker OR venue
    # displayed depth. Broker liquidity is not a quote-activity substitute.
    # Preserve explicit/stronger evidence precedence: an invalid supplied venue
    # input must fail its own validation, never hide behind broker fallback.
    if key=='dom_imbalance' and not source:return evidence.get('VENUE_NATIVE_CHAIN_BOOK') or evidence.get('VENUE_L2_CHECKSUM_BOOK') or evidence.get('BROKER_DEPTH')
    return source
