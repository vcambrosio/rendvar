import investpy

try:
    # Verificar se há alguma funcionalidade relacionada a opções
    print("Métodos disponíveis em investpy:")
    methods = [method for method in dir(investpy) if not method.startswith('_')]
    print(methods)
    
    # Tentar buscar pela função de busca genérica
    print("\nBuscando opções via search_quotes:")
    resultados = investpy.search_quotes(text='PETR', 
                                      products=['options'], 
                                      countries=['brazil'])
    for res in resultados[:3]:
        print(f"Símbolo: {res.symbol}")
        print("---")
        
except Exception as e:
    print(f"Erro: {e}")