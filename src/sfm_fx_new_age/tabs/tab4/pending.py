"""Human-confirmed cancellation through the existing shared order owner."""
from PySide6.QtWidgets import QPushButton,QMessageBox
from sfm_fx_new_age.ui.inspection_panels import InspectionPanel,row_context
from sfm_fx_new_age.contracts.analytics import digest


class PendingOrdersPanel(InspectionPanel):
    def __init__(self,*args):
        super().__init__(*args)
        self.cancel_pending=QPushButton('Cancel selected pending order…');self.cancel_pending.setObjectName('cancelSelectedPendingOrder')
        self.cancel_pending.setToolTip('Separate broker cancellation. Requires the selected locally correlated ACCEPTED_PENDING order and exact identity confirmation. No blind retry on UNKNOWN.')
        self.cancel_pending.clicked.connect(self._request_cancel);self.layout().insertWidget(self.layout().count()-1,self.cancel_pending)
        self._cancel_dialog=None;self._selected()
    def _selected(self):
        super()._selected()
        if not hasattr(self,'cancel_pending'):return
        row=self.selected() or {}
        valid=bool(row.get('id') and row.get('client_order_id') and row.get('broker_order_id') and row.get('state')=='ACCEPTED_PENDING')
        self.cancel_pending.setEnabled(valid and self._cancel_dialog is None)
    def _request_cancel(self):
        row=self.selected()
        if not row or not self.cancel_pending.isEnabled() or self._cancel_dialog:return
        try:context=row_context(self.api,row,frame=(self.context or {}).get('timeframe'))
        except ValueError as exc:self.feedback.setText(str(exc));return
        order_id=row['id'];scope=row['scope_id'];order_hash=digest(row)
        box=QMessageBox(self);box.setObjectName('confirmPendingCancellation');box.setWindowTitle('Confirm pending-order cancellation')
        box.setIcon(QMessageBox.Warning)
        box.setText('Cancel only this pending order?')
        box.setInformativeText('\n'.join((row['symbol']+' '+row['side']+' · '+str(row['units'])+' units @ '+str(row['entry_price']),
            'Account: '+row['account_id']+' · '+row['endpoint_class'],
            'Broker order: '+row['broker_order_id'],'Local order: '+order_id,
            'A fill may race this request. UNKNOWN requires reconciliation, not another cancellation.')))
        box.setStandardButtons(QMessageBox.Yes|QMessageBox.No);box.setDefaultButton(QMessageBox.No)
        self._cancel_dialog=box;self._selected()
        def finished(code):
            self._cancel_dialog=None
            if code==QMessageBox.Yes:
                try:
                    self.api.validate_inspection(context)
                    current=self.selected()
                    if not current or current.get('id')!=order_id or digest(current)!=order_hash:
                        raise ValueError('Selection changed; inspect and confirm the pending order again')
                    result=self.api.command('4.3','SEPARATE_BROKER_CANCEL',{'order_id':order_id,'user_initiated':True,
                        'expected_order_hash':order_hash,'expected_scope_id':scope})
                    self.feedback.setText(result.status.value+': '+result.message+(' · Await reconciliation; never blind retry' if 'UNKNOWN' in result.message else ' · Separate from local signal cancellation'))
                    if result.status.value=='ACCEPTED':
                        # The command deliberately changes this record hash. Follow
                        # its current state, not the now-stale pre-confirmation pin.
                        self.context=None;self._cursor=0;self._expected=None
                except ValueError as exc:self.feedback.setText('Cancellation refused: '+str(exc))
                self.refresh()
                for i,row in enumerate(self._rows):
                    if row.get('id')==order_id:self.table.selectRow(i);break
            self._selected();box.deleteLater()
        box.finished.connect(finished);box.open()
