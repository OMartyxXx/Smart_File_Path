from . import properties, operators, panels, updater


def register():
    updater.register()
    properties.register()
    operators.register()
    panels.register()


def unregister():
    panels.unregister()
    operators.unregister()
    properties.unregister()
    updater.unregister()
