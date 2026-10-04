import json

import pyperclip

from assistant_core.database.models import SessionLocal
from assistant_core.database.models import User, Role
from common.encryption_service import encrypt_list, decrypt_list
from voice_biometrics.db import get_session
from voice_utils import record_and_build_embedding, test_embedding

#
# ОТДЕЛЬНЫЙ МОДУЛЬ ДЛЯ СОЗДАНИЯ РОЛЕЙ И ПОЛЬЗОВАТЕЛЕЙ
#


# ---------- HELPERS ----------

def pause():
    input("\nEnter для продолжения...")


def list_users(session):
    users = session.query(User).all()
    if not users:
        print("Пользователей нет")
        return []

    for u in users:
        print(f"{u.id} | {u.username} | {u.role.name}")

    return users


def list_roles(session):
    roles = session.query(Role).all()
    if not roles:
        print("Ролей нет")
        return []

    for r in roles:
        print(f"{r.id} | {r.name} | access={r.access_level}")

    return roles


def get_user_by_input(session, value):
    return session.query(User).filter(
        (User.id == value) | (User.username == value)
    ).first()


def get_role_by_input(session, value):
    return session.query(Role).filter(
        (Role.id == value) | (Role.name == value)
    ).first()


# ---------- USERS ----------

def create_user():
    session = get_session()

    username = input("Имя пользователя: ")

    if session.query(User).filter_by(username=username).first():
        print("Такой пользователь уже существует")
        return

    roles = list_roles(session)
    if not roles:
        print("Сначала создайте роль")
        return

    role_value = input("ID или имя роли: ")
    role = get_role_by_input(session, role_value)

    if not role:
        print("Роль не найдена")
        return

    print("\nЗапись голосового профиля...")
    embedding = record_and_build_embedding()

    user = User(
        username=username,
        role_id=role.id,
        voice_embedding=encrypt_list(embedding)
    )

    session.add(user)
    session.commit()

    print("Пользователь создан!")

    if input("Протестировать распознавание? (y/n): ").lower() == "y":
        sim = test_embedding(embedding)
        print(f"Similarity: {sim:.3f}")


def edit_user(user):
    session = get_session()

    while True:
        print("""
1 — изменить имя
2 — изменить роль
3 — перезаписать голос
4 — проверить голос
5 - просмотреть дешифрованный voice embedding
6 — назад
""")

        choice = input("> ")

        if choice == "1":
            user.username = input("Новое имя: ")
            session.commit()

        elif choice == "2":
            list_roles(session)
            role_value = input("ID или имя роли: ")
            role = get_role_by_input(session, role_value)
            if role:
                user.role_id = role.id
                session.commit()

        elif choice == "3":
            print("Перезапись голосового профиля...")
            user.voice_embedding = encrypt_list(record_and_build_embedding())
            session.commit()
            print("Голос обновлён")

        elif choice == "4":
            print("\nПроверка голосового совпадения...")
            sim = test_embedding(decrypt_list(user.voice_embedding))
            print(f"Similarity: {sim:.3f}")

            if sim > 0.8:
                print("✅ Голос совпадает")
            elif sim > 0.65:
                print("⚠️ Похоже, но неуверенно")
            else:
                print("❌ Не совпадает")

        elif choice == "5":
            print("Дешифрованные эмбеддинги для " + user.username)
            print(decrypt_list(user.voice_embedding))
            print("Эмбеддинги были скопированы в буфер обмена")
            pyperclip.copy(str(decrypt_list(user.voice_embedding)))

        elif choice == "6":
            return


def delete_user():
    session = get_session()
    list_users(session)

    value = input("ID или имя пользователя: ")
    user = get_user_by_input(session, value)

    if not user:
        print("Не найден")
        return

    if input(f"Удалить {user.username}? (yes): ") == "yes":
        session.delete(user)
        session.commit()
        print("Удалён")


def view_users():
    session = get_session()

    while True:
        users = list_users(session)
        if not users:
            return

        print("\nВведите ID/имя для редактирования или Enter для выхода")
        value = input("> ")

        if value == "":
            return

        user = get_user_by_input(session, value)
        if user:
            edit_user(user)


# ---------- ROLES ----------

def create_role():
    session = get_session()

    name = input("Название роли: ")

    if session.query(Role).filter_by(name=name).first():
        print("Такая роль уже существует")
        return

    access = int(input("Access level: "))
    desc = input("Описание: ")

    role = Role(
        name=name,
        access_level=access,
        description=desc
    )

    session.add(role)
    session.commit()

    print("Роль создана!")


def edit_role():
    session = get_session()
    list_roles(session)

    value = input("ID или имя роли: ")
    role = get_role_by_input(session, value)

    if not role:
        print("Роль не найдена")
        return

    role.access_level = int(input("Новый access level: "))
    role.description = input("Новое описание: ")

    session.commit()
    print("Роль обновлена!")


def delete_role():
    session = get_session()
    list_roles(session)

    value = input("ID или имя роли: ")
    role = get_role_by_input(session, value)

    if not role:
        print("Не найдена")
        return

    users = session.query(User).filter(User.role_id == role.id).all()

    if users:
        print("\nНельзя удалить роль — она используется:")
        for u in users:
            print(f"- {u.username}")
        return

    if input(f"Удалить роль {role.name}? (yes): ") == "yes":
        session.delete(role)
        session.commit()
        print("Роль удалена")


def view_roles():
    session = get_session()
    list_roles(session)
    pause()


# ---------- MAIN MENU ----------

def main():
    while True:
        print("""
1 — Создать пользователя
2 — Просмотреть пользователей
3 — Удалить пользователя

4 — Создать роль
5 — Изменить роль
6 — Удалить роль
7 — Просмотреть роли

8 — Выход
""")

        choice = input("> ")

        if choice == "1":
            create_user()

        elif choice == "2":
            view_users()

        elif choice == "3":
            delete_user()

        elif choice == "4":
            create_role()

        elif choice == "5":
            edit_role()

        elif choice == "6":
            delete_role()

        elif choice == "7":
            view_roles()

        elif choice == "8":
            break


if __name__ == "__main__":
    main()