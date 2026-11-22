"""Browser-first cTrader sign-in; credentials and sockets stay in the connector."""
from PySide6.QtCore import Qt,QUrl,QTimer,Signal
from PySide6.QtGui import QDesktopServices,QPainter,QPen,QColor
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QCheckBox,QFileDialog,QFrame,QStyle,QStyleOptionButton
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES


class RememberCheckBox(QCheckBox):
    def paintEvent(self,event):
        super().paintEvent(event)
        if self.isChecked():
            option=QStyleOptionButton();self.initStyleOption(option)
            rect=self.style().subElementRect(QStyle.SE_CheckBoxIndicator,option,self)
            painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor('#0B1220'),2))
            painter.drawLine(rect.left()+3,rect.center().y(),rect.left()+6,rect.bottom()-3)
            painter.drawLine(rect.left()+6,rect.bottom()-3,rect.right()-3,rect.top()+3);painter.end()


class FeedDialog(QDialog):
    def __init__(self,system_api,trading_api,parent=None,*,fixture_mode=False):
        super().__init__(parent);self.system_api=system_api;self.trading_api=trading_api;self.fixture_mode=fixture_mode
        self.setObjectName('ctraderSignIn');self.setWindowTitle('cTrader connection');self.resize(560,410);self.setMinimumWidth(430)
        self.setAttribute(Qt.WA_DeleteOnClose,False);self.last_action=''
        layout=QVBoxLayout(self);layout.setContentsMargins(22,20,22,20);layout.setSpacing(14)
        heading=QLabel('Connect your cTrader account');heading.setProperty('role','heading');layout.addWidget(heading)
        intro=QLabel('Sign in securely in your browser. SFM receives an access token, never your cTrader password.');intro.setWordWrap(True);layout.addWidget(intro)
        self.status=QLabel();self.status.setTextFormat(Qt.PlainText);self.status.setWordWrap(True);self.status.setObjectName('connectionState');layout.addWidget(self.status)
        self.analytical_status=QLabel();self.analytical_status.setTextFormat(Qt.PlainText);self.analytical_status.setWordWrap(True);self.analytical_status.setObjectName('analyticalFeedState');layout.addWidget(self.analytical_status)
        self.setup=QFrame();self.setup.setObjectName('card');box=QVBoxLayout(self.setup)
        setup_title=QLabel('One-time application setup');setup_title.setProperty('role','heading');box.addWidget(setup_title)
        text=QLabel('Already registered a cTrader application? Link that application once; do not register another one. Refreshing a token on the website alone does not send it to SFM.');text.setWordWrap(True);box.addWidget(text)
        self.link_button=QPushButton('Link existing registered application…');self.link_button.setObjectName('linkExistingCtraderApplication');self.link_button.setProperty('role','connect');self.link_button.clicked.connect(self.link_application);box.addWidget(self.link_button)
        row=QHBoxLayout();self.import_button=QPushButton('Import application connection…');self.import_button.setObjectName('importCtraderProfile');self.import_button.clicked.connect(self.import_profile);row.addWidget(self.import_button)
        self.registration=QPushButton('Application portal ↗');self.registration.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://openapi.ctrader.com/apps')));row.addWidget(self.registration);box.addLayout(row)
        layout.addWidget(self.setup)
        snapshot=self._status()
        self.remember=RememberCheckBox('Reconnect automatically when SFM opens');self.remember.setObjectName('rememberCtraderLogin')
        self.remember.setChecked(snapshot.get('auto_login',False) if snapshot.get('remember_preference_set') else True)
        self.remember.setToolTip('The session is saved locally until Sign out. This switch controls automatic startup reconnection, not orders. No cTrader password is stored.');layout.addWidget(self.remember)
        self.accounts=QComboBox();self.accounts.setObjectName('ctraderAccountPicker');self.accounts.setAccessibleName('Authenticated cTrader account');layout.addWidget(self.accounts)
        self.feed=QPushButton('Use account & start data feed');self.feed.setObjectName('startCtraderFeed');self.feed.clicked.connect(self.start_feed);layout.addWidget(self.feed)
        self.accounts.currentIndexChanged.connect(lambda _:self.feed.setEnabled(bool(self.accounts.currentData()) and not self.fixture_mode))
        self.info=QLabel();self.info.setTextFormat(Qt.PlainText);self.info.setWordWrap(True);self.info.setObjectName('connectionAction');layout.addWidget(self.info)
        layout.addStretch()
        buttons=QHBoxLayout();self.login=QPushButton('Sign in with cTrader ↗');self.login.setObjectName('ctraderBrowserSignIn');self.login.setProperty('role','connect');self.login.clicked.connect(self.begin_login);buttons.addWidget(self.login)
        self.sign_out=QPushButton('Sign out');self.sign_out.setObjectName('ctraderSignOut');self.sign_out.clicked.connect(self.forget);buttons.addWidget(self.sign_out)
        self.disconnect=QPushButton('Disconnect');self.disconnect.clicked.connect(lambda:self._run(self.system_api,'2.3','DISCONNECT_FEED'));buttons.addWidget(self.disconnect)
        self.setup_toggle=QPushButton('Application setup…');self.setup_toggle.setCheckable(True);self.setup_toggle.toggled.connect(self.refresh);buttons.addWidget(self.setup_toggle)
        close=QPushButton('Close');close.clicked.connect(self.close);buttons.addWidget(close);layout.addLayout(buttons)
        self.remember.toggled.connect(self.set_remember)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.refresh);self.refresh()

    def _run(self,api,subtab,name,payload=None):
        result=api.command(subtab,name,payload or {});self.last_action=result.message;self.info.setText(self.last_action);self.refresh();return result
    def _status(self):return thaw(self.system_api.query('2.3',DataRequest('connector')))['rows'][0]
    def import_profile(self):
        path,_=QFileDialog.getOpenFileName(self,'Private cTrader application connection','','JSON connection (*.json)')
        if path:self._run(self.system_api,'2.3','IMPORT_CTRADER_PROFILE',{'path':path})
    def link_application(self):
        from .session_link import ApplicationLinkDialog,link_through_api
        config=self._status().get('configuration') or {}
        dialog=ApplicationLinkDialog(self,redirect_uri=config.get('redirect_uri',''),submit=lambda body:link_through_api(self.system_api,body))
        dialog.exec();self.refresh()
    def set_remember(self,enabled):
        if self._status().get('configuration') and not self.fixture_mode:
            self._run(self.trading_api,'4.5','REMEMBER_CTRADER_LOGIN',{'enabled':enabled})
    def begin_login(self):
        status=self._status()
        config=status.get('configuration') or {}
        if config.get('redirect_uri','').startswith('https://openapi.ctrader.com/apps/') and (status['state']=='LOGIN_REQUIRED' or not status.get('saved_session')):
            self.link_application();return
        preference=self._run(self.trading_api,'4.5','REMEMBER_CTRADER_LOGIN',{'enabled':self.remember.isChecked()})
        if preference.status.value!='ACCEPTED':return
        if status.get('saved_session') and status['state']!='LOGIN_REQUIRED':
            self._run(self.system_api,'2.3','CONNECT');return
        result=self._run(self.trading_api,'4.5','HUMAN_OAUTH_LOGIN')
        if result.status.value=='ACCEPTED':
            url=QUrl(self._status().get('oauth_url') or '')
            if url.scheme()=='https' and url.host()=='id.ctrader.com' and url.path()=='/my/settings/openapi/grantingaccess/' and not QDesktopServices.openUrl(url):
                self.info.setText('Browser could not open. Check the system default browser and try Sign in again.')
    def start_feed(self):
        scope=self.accounts.currentData()
        if not scope:return
        selected=self._run(self.trading_api,'4.5','SELECT_ACCOUNT',{'scope_id':scope})
        if selected.status.value=='ACCEPTED':self._run(self.system_api,'2.3','START_MARKET_FEED')
    def forget(self):self._run(self.trading_api,'4.5','SIGN_OUT_CTRADER');self.remember.blockSignals(True);self.remember.setChecked(False);self.remember.blockSignals(False)
    def refresh(self,*args):
        status=self._status();linked=thaw(self.trading_api.query('4.5',DataRequest('accounts')))['rows']
        busy=status['state'] in {'AUTHENTICATING','CONNECTING','APPLICATION_AUTH','WAITING_FOR_HUMAN'}
        if self.fixture_mode:self.status.setText('Fixture session · real cTrader login is disabled.')
        elif status['feed']['state']=='HISTORY_FETCHED':self.status.setText('Connected · chart history received'+(' · market closed; last prices are snapshots, not fresh ticks.' if status['feed'].get('market_open') is False else ''))
        elif status['state']=='WAITING_FOR_HUMAN':self.status.setText('Complete sign-in in your browser. This window can be closed.')
        elif status['state'] in {'LOGIN_REQUIRED','CONNECTION_FAILED'}:self.status.setText(status['reason']+' No orders will be retried.')
        elif status['state']=='APPLICATION_AUTH_FAILED':self.status.setText('Application authentication failed · '+status['reason'])
        elif busy:self.status.setText('Connecting to cTrader…')
        elif status.get('authenticated_scopes'):self.status.setText('cTrader account authenticated · '+status['feed']['state'].replace('_',' ').lower())
        elif status.get('network_started'):self.status.setText('cTrader transport started · awaiting account authentication')
        elif status.get('saved_session'):self.status.setText('Saved login available · reconnect without entering credentials.')
        elif status.get('configuration'):self.status.setText('Application ready · sign in with cTrader.')
        else:self.status.setText('Not connected · application setup required once.')
        feed=status['feed']
        compute=status.get('analytical_compute',{});pool=compute.get('pool') or {}
        if pool:
            self.status.setText(self.status.text()+'\nCPU projection pool: '+str(pool['inflight'])+' active / '+str(pool['max_workers'])+' ceiling · '+str(pool['queued_lanes'])+' coalesced lanes waiting'+(' · stopped: '+pool['error'] if pool.get('error') else '')+'. Broker and database owners remain single-threaded.')
        if feed['state']!='NOT_STARTED':
            missing=feed.get('missing_metadata',[])
            self.status.setText(self.status.text()+'\nHistory: '+str(feed.get('completed_history_jobs',0))+'/'+str(feed.get('required_history_jobs',len(PAIRS)*len(FRAMES)))+' required jobs complete · eligible pairs '+str(len(feed.get('eligible_pairs',[])))+'/'+str(len(PAIRS))+(' · unavailable: '+', '.join(missing) if missing else '')+'.')
        analytical=status.get('analytical_feed',{})
        self.analytical_status.setVisible(analytical.get('enabled',False))
        if analytical.get('enabled'):
            tpo=sum(v=='ADMITTED' for v in analytical.get('tpo',{}).values())
            depth=sum(v=='OBSERVED_BROKER_DEPTH' for v in analytical.get('broker_depth',{}).get('pairs',{}).values())
            mode='activity alternatives enabled' if analytical.get('activity_alternatives') else 'strict genuine-data mode'
            total=str(len(PAIRS))
            self.analytical_status.setText('Native TPO: '+str(tpo)+'/'+total+' pairs · broker DOM: '+str(depth)+'/'+total+' fresh receipts · official context: '+analytical.get('official_context','WAITING').replace('_',' ').lower()+' · '+mode+'. Tick activity / quote direction are not executed volume / aggressors. Broker DOM is observed, not a sequenced full-book claim.')
            venue=analytical.get('public_venue',{})
            if venue:
                traded=len(venue.get('admitted_pairs',{}).get('TRADED_PRINTS',[]));sided=len(venue.get('admitted_pairs',{}).get('AGGRESSOR_PRINTS',[]))
                self.analytical_status.setText(self.analytical_status.text()+'\nKraken public fiat venue: '+venue.get('state','WAITING').replace('_',' ').lower()+' · executions '+str(traded)+'/'+total+' · taker sides '+str(sided)+'/'+total+'. No API key. Separate venue, not broker fills or consolidated FX.')
                checked=len(venue.get('admitted_pairs',{}).get('VENUE_L2_CHECKSUM_BOOK',[]))
                self.analytical_status.setText(self.analytical_status.text()+'\nKraken checksum L2: '+str(checked)+'/'+total+' fresh · top 10 only, not a sequenced full book. Hour archive: '+venue.get('history_state','NOT_ACQUIRED').replace('_',' ').lower()+'.')
                weeks=len(venue.get('admitted_pairs',{}).get('EXECUTED_WEEK_QUANTITIES',[]))
                self.analytical_status.setText(self.analytical_status.text()+'\nExact broker-week quantities: '+str(weeks)+'/'+total+' · '+venue.get('weekly',{}).get('state','WAITING').replace('_',' ').lower()+'. Native days plus original boundary executions; no missing-hour zero fill.')
            book=analytical.get('public_native_book',{})
            if book:
                self.analytical_status.setText(self.analytical_status.text()+'\nBitstamp full public order book: '+str(len(book.get('fresh_pairs',[])))+'/'+total+' fresh · EURUSD / GBPUSD only · '+book.get('state','WAITING').replace('_',' ').lower()+'. Native UUID predecessor chain plus independent full-snapshot corroboration; displayed liquidity only, not executions or broker fills.')
        self.setup.setVisible(not status.get('configuration') or self.setup_toggle.isChecked());self.import_button.setEnabled(not self.fixture_mode and not busy and not status['network_started'])
        self.setup_toggle.setVisible(bool(status.get('configuration')));self.setup_toggle.setEnabled(not busy and not status['network_started'])
        self.link_button.setEnabled(not self.fixture_mode and not busy and not status['network_started'])
        self.registration.setEnabled(not self.fixture_mode);self.remember.setEnabled(not self.fixture_mode)
        self.login.setEnabled(bool(status.get('configuration')) and status['sdk_installed'] and not self.fixture_mode and not busy and not status['network_started'])
        self.login.setText('Reconnect' if status.get('saved_session') and status['state']!='LOGIN_REQUIRED' else 'Sign in with cTrader ↗')
        self.sign_out.setVisible(bool(status.get('saved_session') or status['network_started'] or busy));self.sign_out.setEnabled(not self.fixture_mode)
        self.disconnect.setVisible(bool(status['network_started']));self.disconnect.setEnabled(not self.fixture_mode)
        selected=self.accounts.currentData();keys=tuple(a['scope_id'] for a in linked)
        if keys!=tuple(self.accounts.itemData(i) for i in range(1,self.accounts.count())) or not self.accounts.count():
            self.accounts.clear()
            self.accounts.addItem('Choose an authenticated account…',None)
            for account in linked:self.accounts.addItem(f"{account['broker_id']} · {account['account_id']} · {account['account_type']}",account['scope_id'])
            index=self.accounts.findData(selected)
            if index>=0:self.accounts.setCurrentIndex(index)
        self.accounts.setVisible(bool(linked));self.accounts.setEnabled(bool(linked));self.feed.setVisible(bool(linked));self.feed.setEnabled(bool(self.accounts.currentData()) and not self.fixture_mode)
        endpoint_health=status.get('endpoint_health',{})
        if not self.last_action and endpoint_health:
            self.info.setText(' · '.join(route+': '+value['state'].replace('_',' ').lower() for route,value in endpoint_health.items())+' · Account type does not determine chart eligibility.')
        if not status['sdk_installed'] and not self.fixture_mode:self.info.setText('The optional cTrader SDK must be installed before account sign-in can start.')
    def showEvent(self,event):self.timer.start();self.refresh();super().showEvent(event)
    def closeEvent(self,event):self.timer.stop();super().closeEvent(event)


class FeedCard(QFrame):
    requested=Signal()
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('feedConnectionCard');self.setMinimumWidth(310)
        outer=QHBoxLayout(self);outer.setContentsMargins(12,8,10,8);outer.setSpacing(12)
        column=QVBoxLayout();column.setSpacing(2)
        self.status=QLabel('cTrader · disconnected');self.status.setObjectName('sessionStatus')
        self.account=QLabel('No account selected');self.account.setObjectName('selectedAccount');self.account.setProperty('role','muted')
        for widget in (self.status,self.account):widget.setTextFormat(Qt.PlainText);widget.setWordWrap(True);column.addWidget(widget)
        outer.addLayout(column,1);self.button=QPushButton('Sign in');self.button.setObjectName('feedConnectButton');self.button.setProperty('role','connect')
        self.button.setToolTip('Browser sign-in once, then automatic account and data-feed reconnection')
        self.button.clicked.connect(self.requested);outer.addWidget(self.button)
    def refresh(self,status,account,fixture=False):
        self.status.setText('SYNTHETIC FIXTURE · NO NETWORK' if fixture else 'cTrader · '+status['state'].replace('_',' ').lower())
        self.account.setText('Account '+account.account_id+' · '+account.account_type if account else 'No account selected')
        self.button.setText('Manage' if account else 'Reconnect' if status.get('saved_session') and status['state']!='LOGIN_REQUIRED' else 'Sign in')
        self.button.setEnabled(not fixture)
