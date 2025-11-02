from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, FeedbackRequired, 
    PleaseWaitFewMinutes, ClientError
)
import time
import sys
import os
import random
import json
import schedule
from datetime import datetime, timedelta

# =========================
# ⚙️ CONFIGURAÇÕES
# =========================
USERNAME = "seu_usuario"  # Altere para seu usuário
PASSWORD = "sua_senha"    # Altere para sua senha

# Configurações de segurança
MAX_UNFOLLOWS_PER_RUN = 50           # Máximo por execução
SLEEP_BETWEEN_ACTIONS = 15           # Tempo entre ações
MAX_RETRIES = 3                      # Tentativas em caso de erro

# Configurações do modo automático
AUTO_MODE = True                     # Ativar modo automático
CHECK_INTERVAL_HOURS = 24            # Verificar a cada 24 horas
MAX_DAILY_UNFOLLOWS = 100            # Máximo diário

# =========================
# 🗂️ ARQUIVO DE HISTÓRICO
# =========================
HISTORY_FILE = "unfollow_history.json"

# =========================
# 🛡️ CONFIGURAÇÃO DE SEGURANÇA
# =========================
def setup_client():
    cl = Client()
    
    # Configurações para evitar detecção
    cl.delay_range = [1, 3]
    cl.set_user_agent("Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36")
    
    # Configuração de proxy (opcional)
    # cl.set_proxy("http://user:pass@host:port")
    
    return cl

# =========================
# 📁 GERENCIAMENTO DE HISTÓRICO
# =========================
def load_history():
    """Carrega o histórico de unfollows"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Erro ao carregar histórico: {e}")
    
    return {
        "total_unfollowed": 0,
        "daily_unfollows": {},
        "last_check": None,
        "unfollowed_users": []
    }

def save_history(history):
    """Salva o histórico de unfollows"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Erro ao salvar histórico: {e}")

def can_unfollow_today(history):
    """Verifica se pode fazer mais unfollows hoje"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    if today not in history["daily_unfollows"]:
        history["daily_unfollows"][today] = 0
        save_history(history)
    
    return history["daily_unfollows"][today] < MAX_DAILY_UNFOLLOWS

def update_daily_count(history, count):
    """Atualiza contador diário"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    if today not in history["daily_unfollows"]:
        history["daily_unfollows"][today] = 0
    
    history["daily_unfollows"][today] += count
    history["total_unfollowed"] += count
    history["last_check"] = datetime.now().isoformat()
    save_history(history)

def add_unfollowed_users(history, users):
    """Adiciona usuários à lista de unfollowed"""
    for user in users:
        user_info = {
            "username": user.username,
            "user_id": user.pk,
            "unfollowed_at": datetime.now().isoformat()
        }
        history["unfollowed_users"].append(user_info)
    
    # Manter apenas os últimos 1000 registros
    if len(history["unfollowed_users"]) > 1000:
        history["unfollowed_users"] = history["unfollowed_users"][-1000:]
    
    save_history(history)

# =========================
# 🔐 LOGIN SEGURO
# =========================
def login_client(cl, username, password):
    try:
        print("🔐 Tentando login...")
        
        # Tenta carregar sessão existente
        try:
            cl.load_settings("session.json")
            cl.get_timeline_feed()
            print("✅ Sessão carregada com sucesso!")
            return True
        except:
            print("🔄 Criando nova sessão...")
            cl.login(username, password)
            cl.dump_settings("session.json")
            print("✅ Login bem-sucedido!")
            return True
            
    except (LoginRequired, ChallengeRequired) as e:
        print(f"❌ Erro de login: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado no login: {e}")
        return False

# =========================
# 📊 OBTER DADOS COM SEGURANÇA
# =========================
def get_user_data(cl):
    try:
        print("📥 Obtendo lista de seguidores...")
        user_id = cl.user_id
        followers = cl.user_followers(user_id)
        print(f"✅ {len(followers)} seguidores encontrados.")

        print("📤 Obtendo lista de quem você segue...")
        following = cl.user_following(user_id)
        print(f"✅ Você segue {len(following)} contas.\n")
        
        return followers, following
        
    except PleaseWaitFewMinutes as e:
        print(f"⏳ Instagram solicitou pausa: {e}")
        wait_time = random.randint(600, 1200)  # 10-20 minutos
        print(f"🕒 Aguardando {wait_time//60} minutos...")
        time.sleep(wait_time)
        return get_user_data(cl)  # Tenta novamente
        
    except Exception as e:
        print(f"❌ Erro ao obter dados: {e}")
        return None, None

# =========================
# 🔍 IDENTIFICAR NÃO-SEGUIDORES
# =========================
def find_non_followers(followers, following, history):
    if not followers or not following:
        return []
        
    followers_ids = set(followers.keys())
    following_ids = set(following.keys())

    non_followers_ids = following_ids - followers_ids
    non_followers = [following[uid] for uid in non_followers_ids]

    # Filtrar usuários que já foram unfollowed
    unfollowed_ids = {user["user_id"] for user in history["unfollowed_users"]}
    non_followers = [user for user in non_followers if user.pk not in unfollowed_ids]

    print(f"🔎 Encontradas {len(non_followers)} contas que não te seguem de volta.\n")
    return non_followers

# =========================
# 🚫 EXECUTAR UNFOLLOWS
# =========================
def execute_unfollows(cl, non_followers, max_unfollows, history):
    if not non_followers:
        print("✅ Nenhum unfollow necessário.")
        return 0, []

    # Verificar limite diário
    remaining_daily = MAX_DAILY_UNFOLLOWS - history["daily_unfollows"].get(
        datetime.now().strftime("%Y-%m-%d"), 0
    )
    
    if remaining_daily <= 0:
        print("📊 Limite diário de unfollows atingido!")
        return 0, []
    
    # Ajustar máximo considerando limite diário
    actual_max = min(max_unfollows, remaining_daily, len(non_followers))
    
    count = 0
    unfollowed_users = []
    print(f"🚀 Iniciando unfollow de até {actual_max} contas...\n")

    for user in non_followers[:actual_max]:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"🔄 Tentando unfollow @{user.username} (tentativa {attempt + 1})...")
                cl.user_unfollow(user.pk)
                print(f"❌ Deixou de seguir: @{user.username}")
                count += 1
                unfollowed_users.append(user)
                
                # Tempo aleatório entre ações
                sleep_time = SLEEP_BETWEEN_ACTIONS + random.randint(-5, 10)
                print(f"⏳ Aguardando {sleep_time} segundos...")
                time.sleep(sleep_time)
                break
                
            except PleaseWaitFewMinutes as e:
                print(f"⏳ Limitação do Instagram: {e}")
                wait_time = random.randint(600, 1800)  # 10-30 minutos
                print(f"🕒 Aguardando {wait_time//60} minutos...")
                time.sleep(wait_time)
                continue
                
            except ClientError as e:
                if "wait a few minutes" in str(e).lower():
                    print("⏳ Instagram pediu para esperar...")
                    time.sleep(300)  # 5 minutos
                    continue
                else:
                    print(f"⚠️ Erro ao deixar de seguir @{user.username}: {e}")
                    time.sleep(10)
                    break
                    
            except Exception as e:
                print(f"⚠️ Erro inesperado com @{user.username}: {e}")
                time.sleep(10)
                break

    return count, unfollowed_users

# =========================
# 📊 MOSTRAR ESTATÍSTICAS
# =========================
def show_statistics(history):
    print("\n" + "="*50)
    print("📊 ESTATÍSTICAS DO BOT")
    print("="*50)
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily_count = history["daily_unfollows"].get(today, 0)
    
    print(f"📈 Total de unfollows: {history['total_unfollowed']}")
    print(f"📅 Unfollows hoje: {daily_count}/{MAX_DAILY_UNFOLLOWS}")
    print(f"📋 Histórico salvo: {len(history['unfollowed_users'])} usuários")
    
    if history["last_check"]:
        last_check = datetime.fromisoformat(history["last_check"])
        print(f"⏰ Última verificação: {last_check.strftime('%d/%m/%Y %H:%M')}")
    
    print("="*50)

# =========================
# 🔧 MODO MANUAL
# =========================
def manual_mode(cl, history):
    print("\n🎮 MODO MANUAL ATIVADO")
    
    while True:
        print("\nOpções:")
        print("1. Ver estatísticas")
        print("2. Executar unfollows agora")
        print("3. Verificar não-seguidores")
        print("4. Sair")
        
        choice = input("\nEscolha uma opção (1-4): ").strip()
        
        if choice == "1":
            show_statistics(history)
            
        elif choice == "2":
            if not can_unfollow_today(history):
                print("❌ Limite diário atingido!")
                continue
                
            followers, following = get_user_data(cl)
            if followers and following:
                non_followers = find_non_followers(followers, following, history)
                if non_followers:
                    count, unfollowed = execute_unfollows(
                        cl, non_followers, MAX_UNFOLLOWS_PER_RUN, history
                    )
                    if count > 0:
                        update_daily_count(history, count)
                        add_unfollowed_users(history, unfollowed)
                        print(f"\n✅ {count} unfollows realizados com sucesso!")
                else:
                    print("✅ Nenhum não-seguidor encontrado!")
                    
        elif choice == "3":
            followers, following = get_user_data(cl)
            if followers and following:
                non_followers = find_non_followers(followers, following, history)
                print(f"\n📋 Não-seguidores encontrados: {len(non_followers)}")
                if non_followers:
                    print("\nPrimeiros 10 não-seguidores:")
                    for i, user in enumerate(non_followers[:10]):
                        print(f"  {i+1}. @{user.username}")
                        
        elif choice == "4":
            print("👋 Saindo do modo manual...")
            break
            
        else:
            print("❌ Opção inválida!")

# =========================
# 🤖 MODO AUTOMÁTICO
# =========================
def auto_unfollow_job():
    """Função executada automaticamente pelo agendador"""
    print(f"\n🤖 EXECUÇÃO AUTOMÁTICA - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    history = load_history()
    
    if not can_unfollow_today(history):
        print("📊 Limite diário já atingido. Próxima verificação em 24h.")
        return
    
    cl = setup_client()
    
    if login_client(cl, USERNAME, PASSWORD):
        followers, following = get_user_data(cl)
        
        if followers and following:
            non_followers = find_non_followers(followers, following, history)
            
            if non_followers:
                count, unfollowed = execute_unfollows(
                    cl, non_followers, MAX_UNFOLLOWS_PER_RUN, history
                )
                
                if count > 0:
                    update_daily_count(history, count)
                    add_unfollowed_users(history, unfollowed)
                    print(f"🤖 Execução automática: {count} unfollows realizados")
                else:
                    print("🤖 Nenhum unfollow necessário desta vez")
            else:
                print("🤖 Todos te seguem de volta! 🎉")
        
        # Salvar sessão
        try:
            cl.dump_settings("session.json")
        except:
            pass

def setup_auto_mode():
    """Configura o agendamento automático"""
    print("🤖 Configurando modo automático...")
    print(f"⏰ Verificações a cada {CHECK_INTERVAL_HOURS} horas")
    print(f"📊 Máximo de {MAX_DAILY_UNFOLLOWS} unfollows por dia")
    
    # Agendar execução
    schedule.every(CHECK_INTERVAL_HOURS).hours.do(auto_unfollow_job)
    
    # Executar imediatamente na primeira vez
    print("🚀 Executando primeira verificação agora...")
    auto_unfollow_job()
    
    print(f"\n✅ Bot automático configurado! Verificando a cada {CHECK_INTERVAL_HOURS}h")
    print("💡 Pressione Ctrl+C para parar o bot")

# =========================
# 🎯 FUNÇÃO PRINCIPAL
# =========================
def main():
    print("=" * 60)
    print("🤖 BOT INSTAGRAM UNFOLLOW - AUTO & MANUAL")
    print("=" * 60)
    
    # Verificar credenciais
    if USERNAME == "seu_usuario" or PASSWORD == "sua_senha":
        print("❌ Configure USERNAME e PASSWORD no script!")
        sys.exit(1)
    
    # Carregar histórico
    history = load_history()
    show_statistics(history)
    
    # Configurar cliente
    cl = setup_client()
    
    # Fazer login
    if not login_client(cl, USERNAME, PASSWORD):
        print("❌ Falha no login. Verifique suas credenciais.")
        sys.exit(1)
    
    # Escolher modo de operação
    if AUTO_MODE:
        print("\n🎯 Modo: AUTOMÁTICO")
        print("💡 Dica: Altere AUTO_MODE = False para usar o modo manual")
        
        # Executar uma vez manualmente primeiro
        auto_unfollow_job()
        
        # Configurar agendamento
        setup_auto_mode()
        
        # Manter o script rodando
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verificar agendamentos a cada minuto
        except KeyboardInterrupt:
            print("\n👋 Bot interrompido pelo usuário")
            
    else:
        print("\n🎯 Modo: MANUAL")
        manual_mode(cl, history)

if __name__ == "__main__":
    main()
