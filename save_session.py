from instagrapi import Client

# ===============================
# Faça login uma única vez
# ===============================
USERNAME = input("Digite seu usuário: ")
PASSWORD = input("Digite sua senha: ")

cl = Client()
cl.login(USERNAME, PASSWORD)

# Salva os dados da sessão
cl.dump_settings("session.json")

print("\n✅ Sessão salva com sucesso em session.json!")
print("Agora copie o conteúdo do arquivo e adicione no GitHub Secrets como IG_SESSION.")