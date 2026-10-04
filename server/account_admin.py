"""Run with privileged local access to reset an account's password."""

import argparse
import asyncio
import getpass

from server.account_store import AccountError, AccountStore


async def reset(username, database):
    password = getpass.getpass("输入新密码（15–128 个字符，不回显）：")
    confirmation = getpass.getpass("再次输入新密码：")
    if password != confirmation:
        raise AccountError(400, "mismatch", "两次密码不同，未修改")
    store = AccountStore(database)
    try:
        await store.reset_password(username, password)
    finally:
        await store.close()
    print("密码已重置，旧登录会话已撤销。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("--db", default="/var/lib/mia/accounts.sqlite3")
    args = parser.parse_args()
    try:
        asyncio.run(reset(args.username, args.db))
    except AccountError as error:
        parser.exit(1, str(error) + "\n")
