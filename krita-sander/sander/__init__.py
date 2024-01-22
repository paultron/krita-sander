from krita import * #DockWidgetFactory, DockWidgetFactoryBase
from .sander import Sander

DOCKER_ID = 'sander'
instance = Krita.instance()
dock_widget_factory = DockWidgetFactory(DOCKER_ID,
                                        DockWidgetFactoryBase.DockRight,
                                        Sander)

instance.addDockWidgetFactory(dock_widget_factory)
