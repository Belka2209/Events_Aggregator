class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *arg, **kwargs):
        if cls not in cls._instances:
            # Создаем экземпляр класса
            cls._instances[cls] = super().__class__(*arg, **kwargs)

        return cls._instances[cls]


class DataBase(metaclass=SingletonMeta):
    def __init__(self, connection_str="default"):
        self.connection_str = connection_str
        print(f"Инициализация БД с параметром: {connection_str}")

    def query(self, sql):
        return f"Выполняем запрос: {sql}, на {self.connection_str}"


db1 = DataBase("prod")
db2 = DataBase("dev")  # Пример игнорируется т.к. экземплятр уже есть

print(db1=db2)
print(db1.query("Select * from user"))
print(db2.query("Select * from animals"))
