import os
import time
import sys
import logging
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, FeedbackRequired, PleaseWaitFewMinutes
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configurações
USERNAME = os.getenv('INSTA_USERNAME')
PASSWORD = os.getenv('INSTA_PASSWORD')
MAX_UNFOLLOWS = int(os.getenv('MAX_UNFOLLOWS', 100))
SLEEP_BETWEEN_ACTIONS = int(os.getenv('SLEEP_BETWEEN_ACTIONS', 10))
SESSION_FILE = "instagram_session.json"

def challenge_code_handler(username, choice):
    """
    Handler para receber o código de verificação
    """
    if choice == ChallengeRequired.EMAIL:
        print(f"Verificação por email enviada para {username}")
    elif choice == ChallengeRequired.SMS:
        print(f"Verificação por SMS enviada para {username}")
    
    while True:
        code = input("Digite o código de 6 dígitos recebido: ").strip()
        if code and code.isdigit() and len(code) == 6:
            return code
        print("Código inválido. Digite exatamente 6 dígitos.")

def setup_client():
    """
    Configura o cliente Instagram com session management
    """
    cl = Client()
    
    # Tentar carregar sessão existente
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            logging.info('Sessão anterior carregada.')
        except Exception as e:
            logging.warning(f'Erro ao carregar sessão: {e}')
    
    # Configurar handler de challenge
    cl.challenge_code_handler = challenge_code_handler
    
    return cl

def main():
    if not USERNAME or not PASSWORD:
        logging.error('Usuário ou senha não configurados nas variáveis de ambiente.')
        sys.exit(1)

    cl = setup_client()

    try:
        logging.info('Efetuando login...')
        cl.login(USERNAME, PASSWORD)
        
        # Salvar sessão para uso futuro
        cl.dump_settings(SESSION_FILE)
        logging.info('Login bem-sucedido e sessão salva!')
        
    except (LoginRequired, ChallengeRequired, FeedbackRequired) as e:
        logging.error(f'Erro no login: {e}')
        sys.exit(1)

    # Resto do código permanece igual...
    try:
        logging.info('Obtendo lista de seguidores...')
        followers = cl.user_followers(cl.user_id)
        logging.info(f'{len(followers)} seguidores encontrados.')

        logging.info('Obtendo lista de quem você segue...')
        following = cl.user_following(cl.user_id)
        logging.info(f'Você segue {len(following)} contas.')

    except PleaseWaitFewMinutes as e:
        logging.warning(f'O Instagram solicitou pausa: {e}')
        sys.exit(1)

    followers_ids = set(followers.keys())
    following_ids = set(following.keys())

    non_followers_ids = following_ids - followers_ids
    non_followers = [following[uid] for uid in non_followers_ids]

    logging.info(f'Encontradas {len(non_followers)} contas que não te seguem de volta.')

    if not non_followers:
        logging.info('Nenhum unfollow necessário.')
        sys.exit(0)

    count = 0
    logging.info(f'Iniciando unfollow de até {MAX_UNFOLLOWS} contas...')

    for user in non_followers[:MAX_UNFOLLOWS]:
        try:
            cl.user_unfollow(user.pk)
            logging.info(f'Deixou de seguir: @{user.username}')
            count += 1
            time.sleep(SLEEP_BETWEEN_ACTIONS)
        except PleaseWaitFewMinutes as e:
            logging.warning(f'Aguardando devido a limitação: {e}')
            time.sleep(600)
            continue
        except Exception as e:
            logging.error(f'Erro ao deixar de seguir @{user.username}: {e}')
            time.sleep(10)

    logging.info(f'Processo concluído! {count} contas deixadas de seguir.')

if __name__ == '__main__':
    main()