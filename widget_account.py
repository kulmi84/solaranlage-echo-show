"""Silent per-instance widget initialization using normal account linking.

Appended to the existing deployed handler. Fullscreen functions stay unchanged.
"""
import copy
import re

WIDGET_ACCOUNT_EVENT='solar.widget.images.v1'
WIDGET_ACCOUNT_SKILL='amzn1.ask.skill.ac1da0c3-87cc-416e-a898-54033b6f0551'
WIDGET_ACCOUNT_PACKAGES=('SolarImageStatus102','SolarImageLive112')


def route_widget_account(event, context, handler, session_factory, config_factory, access_factory):
    request=event.get('request',{})
    if request.get('type')!='Alexa.Presentation.APL.UserEvent' or request.get('arguments') not in ([WIDGET_ACCOUNT_EVENT], ['solar.widget.open.v1']):
        return handler(event,context)
    system=event.get('context',{}).get('System',{})
    uri=request.get('presentationUri','')
    packages='|'.join(re.escape(p) for p in WIDGET_ACCOUNT_PACKAGES)
    pattern=r'widget://'+re.escape(WIDGET_ACCOUNT_SKILL)+r'(?:_development)?/(?:'+packages+r')/[A-Za-z0-9_.:-]{1,300}'
    response={'shouldEndSession':True}
    if system.get('application',{}).get('applicationId')!=WIDGET_ACCOUNT_SKILL or not re.fullmatch(pattern,uri):
        return {'version':'1.0','response':response}
    if request.get('arguments')==['solar.widget.open.v1']:
        launch=copy.deepcopy(event)
        launch['request']={**request,'type':'LaunchRequest'}
        launch['request'].pop('arguments',None)
        return handler(launch,context)
    commands=[]
    access=access_factory(event)
    if not access:
        commands=[{'type':'SetValue','componentId':'imageWidget','property':'accountMessage',
                   'value':'Bitte Solaranlage in der Alexa-App verknüpfen.'}]
    else:
        try:
            grant=session_factory(access,config_factory())
            base=grant['base_url']
            prefix='https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s='
            if not base.startswith(prefix) or not re.fullmatch(r'[A-Za-z0-9_-]{40,1000}',base[len(prefix):]):
                raise ValueError('Invalid image grant')
            lifetime=grant.get('expires_in')
            if type(lifetime) is not int or not 60<=lifetime<=86400:
                raise ValueError('Invalid image lifetime')
            origin='https://solaranlage-display.kulmi84.workers.dev/widget/'
            token=base[len(prefix):]
            values=[('imageBase',origin+'value.png?s='+token),
                    ('statusImageBase',origin+'status.png?s='+token),
                    ('grantReady',True),('accountMessage',''),
                    ('grantRefreshAt','${elapsedTime + '+str(max(30000,min(43200000,lifetime*1000-30000)))+'}'),
                    ('imageNonce','${elapsedTime}')]
            commands=[{'type':'SetValue','componentId':'imageWidget','property':name,'value':value} for name,value in values]
        except Exception:
            # Keep last URLs/values through transient errors. Do not log the grant.
            commands=[{'type':'SetValue','componentId':'imageWidget','property':'accountMessage',
                       'value':'Verbindung wird erneut versucht.'}]
    response['directives']=[{'type':'Alexa.Presentation.APL.ExecuteCommands','presentationUri':uri,'commands':commands}]
    return {'version':'1.0','response':response}

