# Auditoria legislativa federal

Objetivo: inventário verificável da legislação federal brasileira para comparação de dispositivos e investigação de conflitos, ambiguidades, redundâncias, lacunas, obsolescência e oportunidades de consolidação.

## Execução instalada

GitHub Actions cataloga e baixa automaticamente os documentos candidatos do acervo `ctresb/leis`, nos diretórios federal, reguladores, tratados e na Constituição. A versão da fonte está congelada no código. Árvores truncadas são subdivididas; cada download é conferido pelo hash Git. Textos, links presentes, marcadores de artigos, manifesto e falhas são reunidos nos artefatos da execução, retidos por 90 dias. O processamento inicia com mudanças no código ou pelo botão Run workflow. Não há tarefa diária.

## Limites e próximas etapas necessárias

Este primeiro motor é documental. Não faz análise jurídica nem determina vigência. A cobertura do repositório secundário não é a cobertura de toda a legislação brasileira. Arquivos, anexos e versões não equivalem a normas únicas. Os lotes anteriores da conversa ainda não foram reconciliados com este inventário.

Para chegar ao comparativo final: reconciliar identidades e versões; confrontar fontes oficiais e vigência; segmentar dispositivos completos (incluindo parágrafos e incisos); mapear relações e assuntos; avaliar candidatos a conflitos levando em conta hierarquia, especialidade, temporalidade e jurisprudência pertinente; registrar evidências, contrapontos e propostas verificáveis. Similaridade textual nunca deve ser apresentada como prova de conflito jurídico.

A entrega final deve comparar normas lado a lado, com dispositivos, fontes, alcance, justificativa, grau de certeza e propostas. Contagens intermediárias não são a conclusão solicitada.

## Validação local

`python -m unittest discover -s tests -v`

## Comparação automática instalada

Ao terminar com sucesso o inventário, o workflow **Comparação documental federal** recupera seus artefatos e executa a triagem sem nova intervenção. Também aceita o ID de um inventário concluído pelo botão Run workflow. Falha ou cancelamento da coleta não são apresentados como cobertura completa.

O artefato `comparacao-federal-<execução>` contém:

- `comparativo.html`: artigos completos lado a lado, com arquivo, linha e ligação para o texto coletado;
- `candidatos.jsonl`: pares selecionados por proximidade lexical, sinais observados e verificações jurídicas pendentes;
- `comparacao.sqlite`: todos os blocos de artigos reconhecidos e índice de busca;
- `cobertura_comparacao.json`: quantidade de artigos, pares recuperados, pares possíveis entre arquivos e consultas que atingiram o limite;
- `segmentacao_pendencias.jsonl`: documentos cujo formato não permitiu reconhecer artigos.

A busca usa até oito termos de cada artigo e recupera até doze vizinhos de outros arquivos; o filtro Jaccard padrão é 0,28. Os parâmetros e a saturação aparecem na cobertura. Nenhum resultado é denominado conflito confirmado automaticamente. Artigos com poucos termos, textos com outra formatação, diferenças entre versões da mesma norma, normas sem semelhança lexical e relações dependentes de contexto exigem outras etapas. Esta triagem **não resolve por si só ambiguidades, lacunas ou a análise jurídica integral**. Links oficiais extraídos são apenas candidatos à conferência, não fontes já verificadas.

A identificação por hash e posição distingue artigos de mesma numeração em anexos e no ADCT; não constitui reconciliação de identidade legislativa. O texto do bloco preserva notas e títulos entre artigos para não eliminar ressalvas relevantes. Documentos do acervo secundário, inclusive os que se declaram compilados, precisam de confronto oficial.

O comparativo jurídico final permanece pendente da reconciliação de normas, confirmação de fontes e vigência, avaliação por assunto, jurisprudência e análise dos contrapontos. Não há serviço de IA externo configurado nem promessa de que o GitHub, sozinho, emitirá esse parecer. O usuário não precisa analisar os arquivos intermediários.

## Retomada de coleta

A coleta agora preserva um catálogo e um banco SQLite, com transações a cada 32 documentos. Ao retomar no mesmo diretório, confere novamente o hash dos textos salvos e baixa apenas os ausentes ou inválidos. O workflow restaura e salva esse checkpoint no cache do Actions, enquanto disponível. Artefatos continuam preservados por 90 dias. Um cache expirado exige recuperar o artefato ou refazer a coleta.

`python scripts/inventariar.py --saida resultados` retoma o processamento. Para diagnóstico controlado, `--max-documentos 64` baixa no máximo 64 documentos pendentes e termina com status parcial e código de saída não zero quando ainda faltar material. Isso não autoriza emitir um comparativo integral. O catálogo evita percorrer diretórios auxiliares cujo nome começa por ponto ou sublinhado; esse conteúdo já era excluído do conjunto de documentos analisados.

Em 13/11/2026, as execuções do dia 11 ainda apareciam na fila, sem jobs ou artefatos. Actions estava habilitado; a interface não apresentou a causa da espera. A configuração instalada não significa execução concluída.
