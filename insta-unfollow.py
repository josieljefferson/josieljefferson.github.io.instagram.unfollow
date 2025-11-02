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

# Configurações por variáveis de ambiente para segurança
USERNAME = os.getenv('INSTA_USERNAME')
PASSWORD = os.getenv('INSTA_PASSWORD')
MAX_UNFOLLOWS = int(os.getenv('MAX_UNFOLLOWS', 100))
SLEEP_BETWEEN_ACTIONS = int(os.getenv('SLEEP_BETWEEN_ACTIONS', 10))

def main():
    if not USERNAME or not PASSWORD:
        logging.error('Usuário ou senha não configurados nas variáveis de ambiente.')
        sys.exit(1)

    cl = Client()

    try:
        logging.info('Efetuando login...')
        cl.login(USERNAME, PASSWORD)
        logging.info('Login bem-sucedido!')
    except (LoginRequired, ChallengeRequired, FeedbackRequired) as e:
        logging.error(f'Erro no login: {e}')
        sys.exit(1)

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
            time.sleep(600)  # Espera 10 minutos e continua
            continue
        except Exception as e:
            logging.error(f'Erro ao deixar de seguir @{user.username}: {e}')
            time.sleep(10)

    logging.info(f'Processo concluído! {count} contas deixadas de seguir.')

if __name__ == '__main__':
    main()
