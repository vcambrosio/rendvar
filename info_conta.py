import MetaTrader5 as mt5

# Inicializa conexão
if not mt5.initialize():
    raise SystemExit(f"Erro ao inicializar MT5: {mt5.last_error()}")

# Obtém informações da conta
acct = mt5.account_info()

if acct is None:
    print("Não foi possível obter informações:", mt5.last_error())
else:
    print("=== Situação da conta ===")
    print(f"Saldo (balance): {acct.balance:.2f}")
    print(f"Patrimônio (equity): {acct.equity:.2f}")
    print(f"Margem usada: {acct.margin:.2f}")
    print(f"Margem livre (disponível): {acct.margin_free:.2f}")

mt5.shutdown()
