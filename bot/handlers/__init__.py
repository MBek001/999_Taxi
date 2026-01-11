from . import start, driver, admin, developer, registration, callbacks

def register_all_handlers(dp):
    start.register_handlers(dp)
    registration.register_handlers(dp)
    driver.register_handlers(dp)
    admin.register_handlers(dp)
    developer.register_handlers(dp)
    callbacks.register_handlers(dp)
