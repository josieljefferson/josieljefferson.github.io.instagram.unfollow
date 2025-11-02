import os
import json
import time
import sys
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, FeedbackRequired, PleaseWaitFewMinutes
)

# =========================
# ⚙️ CONFIGURAÇÕES
# =========================
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
SESSION = os.getenv("IG_SESSION")
MAX_UNFOLLOWS = 100
SLEEP_BETWEEN_ACTIONS = 10

# =========================
# 🚀 LOGIN VIA SESSÃO
# =========================
cl = Client()

try:
    if SESSION:
        print("🔐 Restaurando sessão salva...")
        cl.set_settings(json.loads(SESSION))
        cl.login(USERNAME, PASSWORD)
        print("✅ Sessão restaurada com sucesso!\n")
    else:
        print("⚠️ Nenhuma sessão encontrada. Faça login localmente com save_session.py.")
        sys.exit(1)

except (LoginRequired, ChallengeRequired, FeedbackRequired) as e:
    print(f"❌ Erro no login: {e}")
    sys.exit(1)

# =========================
# 👥 OBTENDO DADOS
# =========================
try:
    print("📥 Obtendo lista de seguidores...")
    followers = cl.user_followers(cl.user_id)
    print(f"✅ {len(followers)} seguidores encontrados.")

    print("📤 Obtendo lista de quem você segue...")
    following = cl.user_following(cl.user_id)
    print(f"✅ Você segue {len(following)} contas.\n")

except PleaseWaitFewMinutes as e:
    print(f"⚠️ O Instagram solicitou pausa: {e}")
    sys.exit(1)

# =========================
# 🔍 IDENTIFICANDO NÃO-SEGUIDORES
# =========================
followers_ids = set(followers.keys())
following_ids = set(following.keys())

non_followers_ids = following_ids - followers_ids
non_followers = [following[uid] for uid in non_followers_ids]

print(f"🔎 Encontradas {len(non_followers)} contas que não te seguem de volta.\n")

if not non_followers:
    print("✅ Nenhum unfollow necessário.")
    sys.exit(0)

# =========================
# 🚫 EXECUTANDO UNFOLLOWS
# =========================
count = 0
print(f"🚀 Iniciando unfollow de até {MAX_UNFOLLOWS} contas...\n")

for user in non_followers[:MAX_UNFOLLOWS]:
    try:
        cl.user_unfollow(user.pk)
        print(f"❌ Deixou de seguir: @{user.username}")
        count += 1
        time.sleep(SLEEP_BETWEEN_ACTIONS)

    except PleaseWaitFewMinutes as e:
        print(f"⏳ Aguardando devido a limitação: {e}")
        time.sleep(600)
        continue

    except Exception as e:
        print(f"⚠️ Erro ao deixar de seguir @{user.username}: {e}")
        time.sleep(10)

print(f"\n✅ Processo concluído! {count} contas deixadas de seguir.")