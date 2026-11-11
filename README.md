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
