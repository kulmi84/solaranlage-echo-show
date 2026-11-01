"""Route only the verified account image package; all other requests keep fullscreen behavior."""
WIDGET_SKILL_ID = 'amzn1.ask.skill.4e153616-91b1-4eef-8ede-18cba6a17ecd'
WIDGET_PACKAGE_ID = 'SolarAccountImage'
_widget_fullscreen_handler = lambda_handler


def widget_publish(device, commands):
    credentials = image_config()['widget_datastore_credentials']
    return publish_image_access(device, commands, credentials)


def lambda_handler(event, context):
    return route_account_images(
        event, context, _widget_fullscreen_handler,
        skill_id=WIDGET_SKILL_ID, package_id=WIDGET_PACKAGE_ID,
        access_factory=image_access_token, config_factory=image_config,
        session_factory=create_image_session, publish=widget_publish)
