
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, FeedbackRequired, PleaseWaitFewMinutes
)
import os
import time
import sys
from dotenv import load_dotenv
import logging

# =========================
# ⚙️ CONFIGURAÇÕES E LOGGING
# =========================
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unfollower.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configurações da aplicação
USERNAME = os.getenv('INSTAGRAM_USERNAME')
PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

# Validação das credenciais
if not USERNAME or not PASSWORD:
    logger.error("❌ Credenciais não encontradas. Configure as variáveis de ambiente.")
    sys.exit(1)

MAX_UNFOLLOWS = int(os.getenv('MAX_UNFOLLOWS', 100))
SLEEP_BETWEEN_ACTIONS = int(os.getenv('SLEEP_BETWEEN_ACTIONS', 10))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))

# =========================
# 🚀 CLIENTE INSTAGRAM
# =========================
def create_client():
    """Cria e configura o cliente do Instagram"""
    client = Client()
    
    # Configurações para evitar detecção
    client.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    client.delay_range = [1, 3]
    
    return client

# =========================
# 🔐 LOGIN SEGURO
# =========================
def login_with_retry(client, username, password, max_retries=3):
    """Tenta login com múltiplas tentativas"""
    for attempt in range(max_retries):
        try:
            logger.info(f"🔐 Tentativa de login {attempt + 1}/{max_retries}...")
            client.login(username, password)
            logger.info("✅ Login bem-sucedido!")
            return True
            
        except ChallengeRequired:
            logger.warning("⚠️ Verificação de segurança necessária. Verifique o app do Instagram.")
            if attempt == max_retries - 1:
                logger.error("❌ Falha no login após múltiplas tentativas")
                return False
            time.sleep(30)
            
        except FeedbackRequired as e:
            logger.error(f"❌ Limitação temporária: {e}")
            logger.info("⏳ Aguardando 10 minutos antes de tentar novamente...")
            time.sleep(600)
            
        except PleaseWaitFewMinutes as e:
            logger.warning(f"⏳ Instagram solicitou pausa: {e}")
            wait_time = 600  # 10 minutos
            logger.info(f"🕒 Aguardando {wait_time/60} minutos...")
            time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"❌ Erro inesperado no login: {e}")
            if attempt == max_retries - 1:
                return False
            time.sleep(30)
    
    return False

# =========================
# 📊 OBTER DADOS
# =========================
def get_user_data(client):
    """Obtém lista de seguidores e seguindo"""
    try:
        logger.info("📥 Obtendo lista de seguidores...")
        followers = client.user_followers(client.user_id)
        logger.info(f"✅ {len(followers)} seguidores encontrados.")

        logger.info("📤 Obtendo lista de quem você segue...")
        following = client.user_following(client.user_id)
        logger.info(f"✅ Você segue {len(following)} contas.\n")
        
        return followers, following
        
    except PleaseWaitFewMinutes as e:
        logger.error(f"⏳ Limitação do Instagram: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao obter dados: {e}")
        raise

# =========================
# 🔍 IDENTIFICAR NÃO-SEGUIDORES
# =========================
def find_non_followers(followers, following):
    """Encontra contas que não seguem de volta"""
    followers_ids = set(followers.keys())
    following_ids = set(following.keys())

    non_followers_ids = following_ids - followers_ids
    non_followers = [following[uid] for uid in non_followers_ids]

    logger.info(f"🔎 Encontradas {len(non_followers)} contas que não te seguem de volta.\n")
    
    return non_followers

# =========================
# 🚫 EXECUTAR UNFOLLOWS
# =========================
def execute_unfollows(client, non_followers, max_unfollows, sleep_time):
    """Executa o processo de unfollow"""
    count = 0
    logger.info(f"🚀 Iniciando unfollow de até {max_unfollows} contas...\n")

    for user in non_followers[:max_unfollows]:
        try:
            client.user_unfollow(user.pk)
            logger.info(f"❌ Deixou de seguir: @{user.username}")
            count += 1
            
            # Progresso
            if count % 10 == 0:
                logger.info(f"📊 Progresso: {count}/{min(len(non_followers), max_unfollows)}")
            
            time.sleep(sleep_time)

        except PleaseWaitFewMinutes as e:
            logger.warning(f"⏳ Aguardando devido a limitação: {e}")
            logger.info("🕒 Aguardando 10 minutos...")
            time.sleep(600)
            continue

        except Exception as e:
            logger.error(f"⚠️ Erro ao deixar de seguir @{user.username}: {e}")
            time.sleep(30)  # Espera mais tempo em caso de erro
            continue

    return count

# =========================
# 🎯 FUNÇÃO PRINCIPAL
# =========================
def main():
    """Função principal do script"""
    try:
        # Criar cliente
        cl = create_client()
        
        # Fazer login
        if not login_with_retry(cl, USERNAME, PASSWORD, MAX_RETRIES):
            sys.exit(1)
        
        # Obter dados
        followers, following = get_user_data(cl)
        
        # Encontrar não-seguidores
        non_followers = find_non_followers(followers, following)
        
        if not non_followers:
            logger.info("✅ Nenhum unfollow necessário.")
            return
        
        # Executar unfollows
        count = execute_unfollows(cl, non_followers, MAX_UNFOLLOWS, SLEEP_BETWEEN_ACTIONS)
        
        logger.info(f"✅ Processo concluído! {count} contas deixadas de seguir.")
        
    except KeyboardInterrupt:
        logger.info("⏹️ Processo interrompido pelo usuário.")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
