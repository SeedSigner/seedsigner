class Singleton:
    _instance = None

    def __init__(self):
        # Singleton pattern must prevent normal instantiation
        raise Exception("Cannot directly instantiate a Singleton. Access via get_instance()")

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance



class ConfigurableSingleton(Singleton):
    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance:
            return cls._instance
        else:
            raise Exception("Must call %s.configure_instance() first" % cls.__name__)


    @classmethod
    def configure_instance(cls, config: any = None):
        # Must be called before the first get_instance() call
        if cls._instance:
            raise Exception("Instance already configured")
        
        #TODO: Implementation classes should do something with incoming config
