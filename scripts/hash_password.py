import getpass
import bcrypt

pw = getpass.getpass("Enter password: ")
pw2 = getpass.getpass("Confirm password: ")

if pw != pw2:
    print("Passwords do not match.")
    exit(1)

print(bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
