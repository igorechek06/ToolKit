import logging
import typing as p
from abc import ABC, abstractmethod
from copy import copy
from datetime import datetime
from json import loads, dumps

from aiogram import types as t
from mysql.connector import connect

JSON_DEFAULT = "{}"


def clear_dict(d: dict):
    for k, v in copy(d).items():
        if v is None or v == "" or v == [] or v == {}:
            d.pop(k)
        elif isinstance(v, dict):
            clear_dict(v)
        elif isinstance(v, list):
            clear_list(v)
    return d


def clear_list(l: list):
    for n, v in enumerate(copy(l)):
        if v is None or v == "" or v == [] or v == {}:
            l.pop(n)
        elif isinstance(v, dict):
            clear_dict(v)
        elif isinstance(v, list):
            clear_list(v)
    return l


class _link_obj(ABC):
    _init: bool = False

    _table: str
    _id: int

    def __init__(self, table: str, id: str):
        self._table = table
        self._id = id

        self._init = True

    @abstractmethod
    def get(self, name: str):
        pass

    @abstractmethod
    def set(self, name: str, value: p.Any):
        pass

    def __getattr__(self, name: str):
        name = str(name)
        if self._init:
            return self.get(name)

    def __getitem__(self, name: str):
        name = str(name)
        if name in self.__dict__:
            return self.__dict__[name]
        elif self._init:
            return self.get(name)

    def __setattr__(self, key: str, value: p.Any):
        key = str(key)
        if self._init:
            self.set(key, value)
        else:
            self.__dict__[key] = value

    def __setitem__(self, key: str, value: p.Any):
        key = str(key)
        if self._init:
            self.set(key, value)
        else:
            self.__dict__[key] = value


class settingsOBJ(_link_obj):
    _data: dict

    def __init__(self, settings: str, table: str, id: str):
        self._data = loads(settings)
        super().__init__(table, id)

    def get(self, name):
        if name in self._data:
            return self._data[name]

    def set(self, name: str, value: p.Any):
        from libs.objects import Database
        self._data[name] = value
        Database.update(f"UPDATE {self._table} SET settings='{dumps(clear_dict(self.raw))}' WHERE id={self._id};")

    def values(self):
        return self._data.values()

    def keys(self):
        return self._data.keys()

    def items(self):
        return self._data.items()

    @property
    def sticker_alias(self) -> dict:
        if self["sticker_alias"] is None:
            return {}
        return self["sticker_alias"]

    @property
    def text_alias(self) -> dict:
        if self["text_alias"] is None:
            return {}
        return self["text_alias"]

    @property
    def lang(self) -> str:
        if self["lang"] is None:
            return None
        return self["lang"]

    @property
    def raw(self):
        return self._data


class permissionOBJ(settingsOBJ):
    def __init__(self, permission: str, id: str):
        super().__init__(permission, "Users", id)

    def set(self, name: str, value: p.Any):
        from libs.objects import Database
        self._data[name] = value
        Database.update(f"UPDATE Users SET permission='{dumps(clear_dict(self.raw))}' WHERE id={self._id};")


class reportsOBJ(settingsOBJ):
    def __init__(self, reports: str, id: str):
        super().__init__(reports, "Users", id)

    def get(self, name):
        result = super().get(name)
        return result or 0

    def set(self, name: str, value: p.Any):
        from libs.objects import Database
        self._data[name] = value
        Database.update(f"UPDATE Users SET reports='{dumps(clear_dict(self.raw))}' WHERE id={self._id};")


class userOBJ(_link_obj):
    id: int
    settings: settingsOBJ
    permission: permissionOBJ
    reports: reportsOBJ

    def __init__(self, id: int, settings: str, permission: str, reports: str):
        self.id = id
        self.settings = settingsOBJ(settings, "Users", self.id)
        self.permission = permissionOBJ(permission, self.id)
        self.reports = reportsOBJ(reports, self.id)
        super().__init__("Users", id)

    def get(self, name: str):
        return None

    def set(self, name: str, value: p.Any):
        from libs.objects import Database

        if name in self.__dict__:
            self.__dict__[name] = value

        if name in ["settings", "permission"]:
            value = dumps(clear_dict(value))

        Database.update(f"UPDATE {self._table} SET {name}='{value}' WHERE id={self._id};")


class chatOBJ(_link_obj):
    id: int
    settings: settingsOBJ
    owner: userOBJ

    def __init__(self, id: str, settings: str, owner: int):
        from libs.objects import Database

        self.id = id
        self.settings = settingsOBJ(settings, "Chats", self.id)
        self.owner = Database.get_user(owner)

        super().__init__("Chats", id)

    def get(self, name: str):
        return None

    def set(self, name: str, value: p.Any):
        from libs.objects import Database

        if name in self.__dict__:
            self.__dict__[name] = value

        if name in ["settings", "permission"]:
            value = dumps(clear_dict(value))
        Database.update(f"UPDATE {self._table} SET {name}='{value}' WHERE id={self._id};")


class messageOBJ:
    user_id: int
    chat_id: int
    message: p.Optional[str]
    type: str
    data: str

    def __init__(self, user_id: int, chat_id: int, message: p.Optional[str], type: str, date: datetime):
        self.user_id = user_id
        self.chat_id = chat_id
        self.message = message
        self.type = type
        self.date = date


class Database:
    def __init__(self, host: str, user: str, password: str, database: str) -> None:
        self.connect = connect(
            host=host,
            user=user,
            password=password,
            database=database
        )

    def add_user(self, id: int) -> userOBJ:
        self.update(f"INSERT INTO Users VALUES ({id},{JSON_DEFAULT!r},{JSON_DEFAULT!r},{JSON_DEFAULT!r})")
        return self.get_user(id)

    def add_chat(self, id: int, owner: int) -> chatOBJ:
        self.update(f"INSERT INTO Chats VALUES ({id},{JSON_DEFAULT!r},{owner})")
        return self.get_chat(id)

    def add_message(self, user_id: int, chat_id: int, message: str, type: str, date: datetime) -> messageOBJ:
        if message:
            self.update(
                f"INSERT INTO Messages(user_id,chat_id,message,type,date) VALUES ({user_id},{chat_id},{message!r},{type!r},{date.isoformat(' ')!r})"
            )
        else:
            self.update(
                f"INSERT INTO Messages(user_id,chat_id,type,date) VALUES ({user_id},{chat_id},{type!r},{date.isoformat(' ')!r})"
            )
        return messageOBJ(user_id, chat_id, message, type, date)

    def get_user(self, id: int) -> userOBJ:
        result = self.get(f"SELECT * FROM Users WHERE id={id}", True)

        if not result:
            return self.add_user(id)

        return userOBJ(*result)

    def get_chat(self, id: int, owner: p.Optional[int] = None) -> chatOBJ:
        result = self.get(f"SELECT * FROM Chats WHERE id={id}", True)

        if not result:
            if owner:
                return self.add_chat(id, owner)
            return

        return chatOBJ(*result)

    def get_messages(self,
                     user_id: p.Optional[int] = None,
                     chat_id: p.Optional[int] = None,
                     type: p.Optional[str] = None) -> p.List[messageOBJ]:
        sql = "SELECT * FROM Messages WHERE "
        selectors = []
        if not (user_id and chat_id):
            raise ValueError("user_id or chat_id required")

        if user_id:
            selectors.append(f"user_id = {user_id}")
        if chat_id:
            selectors.append(f"chat_id = {chat_id}")
        if type:
            selectors.append(f"type = {type!r}")
        if not selectors:
            ValueError("Selectors required")

        sql += " AND ".join(selectors)

        result = self.get(sql)
        if result:
            result = self._create_list_of_objects(result, messageOBJ)
        return result

    def get_messages_by_date(self,
                             from_date: datetime,
                             to_date: p.Optional[datetime] = None,
                             contain: bool = True
                             ) -> p.List[messageOBJ]:
        sql = "SELECT * FROM Messages WHERE "

        fd = repr(from_date.isoformat(" "))

        if from_date and to_date:
            td = repr(to_date.isoformat(" "))
            if contain:
                sql += f"date >= {fd} AND date <= {td}"
            else:
                sql += f"date > {fd} AND date < {td}"
        elif from_date:
            sql += f"date = {fd}"

        result = self.get(sql)
        if result:
            result = self._create_list_of_objects(result, messageOBJ)
        return result

    def get_users(self) -> p.List[userOBJ]:
        result = self.get("SELECT * FROM Users")
        return self._create_list_of_objects(result, userOBJ)

    def get_chats(self) -> p.List[chatOBJ]:
        result = self.get("SELECT * FROM Chats")
        return self._create_list_of_objects(result, chatOBJ)

    def get_owns(self, id: int) -> p.List[chatOBJ]:
        result = self.get(f"SELECT * FROM Chats WHERE owner={id}")
        return self._create_list_of_objects(result, chatOBJ)

    def delete_user(self, id: int) -> bool:
        self.update(f"DELETE FROM Uses WHERE id = {id}")

    def delete_chat(self, id: int) -> bool:
        self.update(f"DELETE FROM Messages WHERE chat_id={id}")
        self.update(f"DELETE FROM Chats WHERE id = {id}")

    def get(self, sql: str, one: bool = False) -> p.Union[p.Any, p.List]:
        with self.connect.cursor() as cursor:
            cursor.execute(sql)
            if one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
        return result

    def update(self, sql: str):
        with self.connect.cursor() as cursor:
            cursor.execute(sql)
        self.connect.commit()

    @staticmethod
    def _create_list_of_objects(l: p.List[p.Tuple[p.Any]], o: p.Any):
        return [o(*i) for i in l]


if __name__ == "__main__":
    pass
