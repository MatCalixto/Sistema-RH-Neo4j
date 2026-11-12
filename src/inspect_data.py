
import pandas as pd


#-----------------------------------------------------------
#                      ler o csv
#-----------------------------------------------------------

# Caminho da base de funcionários
arquivo = "data/WA_Fn-UseC_-HR-Employee-Attrition.csv"

# Lê o arquivo
df = pd.read_csv(arquivo)

print("Quantidade de linhas e colunas:")
print(df.shape)

#nomes das colunas
print("\nColunas disponíveis:")
print(df.columns.tolist())

print("\nPrimeiros cinco funcionários:")
print(df.head())

print("\nValores ausentes por coluna:")
print(df.isnull().sum())



# Distribuição de desligamentos
print("\nDistribuição de Attrition:")
print(df["Attrition"].value_counts())

print("\nPercentual de desligamentos:")
print(df["Attrition"].value_counts(normalize=True) * 100)

# Quantidade de funcionários por departamento
print("\nFuncionários por departamento:")
print(df["Department"].value_counts())

# Cargos existentes
print("\nCargos existentes:")
print(df["JobRole"].value_counts())

# Verificação de identificadores duplicados
print("\nEmployeeNumber duplicados:")
print(df["EmployeeNumber"].duplicated().sum())

# Verificação de colunas constantes
print("\nQuantidade de valores únicos por coluna:")
print(df.nunique().sort_values())

#-----------------------------------------------------------
#           verificar maior taxa de desligamento
#-----------------------------------------------------------


df["Attrition_Num"] = (df["Attrition"] == "Yes").astype(int)
# Yes = 1 (desligamento)
# No = 0 (permaneceu)

# Taxa de desligamento por departamento
por_departamento = df.groupby("Department").agg(
    total_funcionarios=("EmployeeNumber", "count"),
    desligamentos=("Attrition_Num", "sum"),
    taxa_desligamento=("Attrition_Num", "mean")
)

por_departamento["taxa_desligamento"] *= 100

print("\nTaxa de desligamento por departamento:")
print(por_departamento.sort_values(
    "taxa_desligamento", ascending=False
).round(2))

# Taxa de desligamento por cargo
por_cargo = df.groupby("JobRole").agg(
    total_funcionarios=("EmployeeNumber", "count"),
    desligamentos=("Attrition_Num", "sum"),
    taxa_desligamento=("Attrition_Num", "mean")
)

por_cargo["taxa_desligamento"] *= 100

print("\nTaxa de desligamento por cargo:")
print(por_cargo.sort_values(
    "taxa_desligamento", ascending=False
).round(2))

print("\nQuantidade de departamentos:")
print(df["Department"].nunique())

print("\nQuantidade de cargos:")
print(df["JobRole"].nunique())

print("\nQuantidade de áreas de formação:")
print(df["EducationField"].nunique())

print("\nColunas do funcionário:")
print(df.iloc[0].to_dict())
