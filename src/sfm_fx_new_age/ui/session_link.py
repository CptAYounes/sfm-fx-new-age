"""One-time registered application handoff, not a cTrader password login.

Sensitive input goes through a private file reference, never through commands/journals.
"""
from __future__ import annotations
import os,tempfile
from pathlib import Path
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLabel,QLineEdit,QPushButton,QHBoxLayout
from sfm_fx_new_age.connector.oauth import OAuthConfig,SecretStore


class ApplicationLinkDialog(QDialog):
    def __init__(self,parent=None,*,redirect_uri='',submit=None):
        super().__init__(parent);self.submit=submit;self.setObjectName('registeredCtraderApplicationLink')
        self.setWindowTitle('Link your registered cTrader application');self.setMinimumWidth(510)
        layout=QVBoxLayout(self);layout.setContentsMargins(22,20,22,20);layout.setSpacing(14)
        title=QLabel('Use your existing registered application');title.setProperty('role','heading');layout.addWidget(title)
        intro=QLabel('One-time setup only. Copy Client ID and Client secret from the application credentials, and the latest Refresh token from its Sandbox. Your cTrader password is not needed.');intro.setWordWrap(True);layout.addWidget(intro)
        form=QFormLayout();self.fields={}
        for key,label,placeholder in [('client_id','Client ID','Application client identifier, not the app page number'),('client_secret','Client secret','From Application credentials'),('refresh_token','Refresh token','Latest token from this application’s Sandbox'),('redirect_uri','Registered redirect','Registered callback or Sandbox URL')]:
            field=QLineEdit();field.setObjectName('appLink_'+key);field.setPlaceholderText(placeholder);field.setMaxLength(8192 if key in ('client_secret','refresh_token') else 2048)
            if key in ('client_secret','refresh_token'):field.setEchoMode(QLineEdit.Password);field.setInputMethodHints(Qt.ImhSensitiveData|Qt.ImhNoPredictiveText)
            if key=='redirect_uri':field.setText(redirect_uri)
            self.fields[key]=field;form.addRow(label,field)
        layout.addLayout(form)
        note=QLabel('Saved in an owner-only local file (not an encrypted keychain). Linking requests authentication and read-only data only; it does not place, cancel or modify orders.');note.setWordWrap(True);note.setProperty('role','muted');layout.addWidget(note)
        self.feedback=QLabel();self.feedback.setObjectName('appLinkFeedback');self.feedback.setTextFormat(Qt.PlainText);self.feedback.setWordWrap(True);layout.addWidget(self.feedback)
        buttons=QHBoxLayout();cancel=QPushButton('Cancel');cancel.clicked.connect(self.reject);buttons.addWidget(cancel);buttons.addStretch()
        self.save=QPushButton('Save & connect');self.save.setObjectName('saveRegisteredCtraderApplication');self.save.setProperty('role','connect');self.save.clicked.connect(self.save_connection);buttons.addWidget(self.save);layout.addLayout(buttons)
    def save_connection(self):
        body={key:field.text().strip() for key,field in self.fields.items()}
        if not all(body.values()):self.feedback.setText('Complete the application fields. Do not enter an account password.');return
        try:
            OAuthConfig(body['client_id'],body['redirect_uri'],'accounts')
            for key in ('client_secret','refresh_token'):
                if any(ch.isspace() for ch in body[key]):raise ValueError('Copy the complete credential without spaces or line breaks.')
            if self.submit is None:raise ValueError('No private application handoff is configured.')
            message=self.submit({**body,'scope':'accounts'})
        except (ValueError,OSError):
            self.feedback.setText('Connection could not be saved. Check the registered redirect and complete credentials; no credential values were logged.');return
        for field in self.fields.values():field.clear()
        self.accept()
    def done(self,result):
        for field in self.fields.values():field.clear()
        super().done(result)


def link_through_api(api,body):
    """Private transient staging; the connector owns the durable store and refresh."""
    scratch=os.environ.get('TMPDIR')
    if not scratch:raise ValueError('Private application scratch directory required')
    with tempfile.TemporaryDirectory(prefix='sfm-application-link-',dir=scratch) as folder:
        store=SecretStore(Path(folder)/'application.json');store.save(body)
        result=api.command('2.3','IMPORT_CTRADER_SESSION',{'path':str(store.path)})
    if result.status.value!='ACCEPTED':raise ValueError('Application connection handoff rejected')
    return result.message
