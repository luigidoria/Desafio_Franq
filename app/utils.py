def formatar_titulo_erro(tipo_erro):
    titulos = {
        'nomes_colunas': 'Nomes das Colunas Incorretos',
        'formato_valor': 'Formato de Valor Monetário Inválido',
        'formato_data': 'Formato de Data Inválido',
        'colunas_faltando': 'Colunas Obrigatórias Ausentes'
    }
    return titulos.get(tipo_erro, 'Erro de Validação')