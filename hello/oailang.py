import os
import openai
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_openai import AzureChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit

openai.base_url = "https://oai-fc-devtwo-ue.openai.azure.com/"
openai.api_type = "azure"
openai.api_version = "2024-02-01"
openai.api_key = "04ff20b86fbe43499f088e3e90cd730a"  # Your Azure OpenAI resource key


def run_oai_sql(query):
    output = ""
    try:
        driver = '{ODBC Driver 17 for SQL Server}'
        odbc_str = 'mssql+pyodbc:///?odbc_connect=' \
                   'Driver=' + driver + \
                   ';Server=tcp:sql-flexcount-devtwo-ue.database.windows.net;PORT=1433' + \
                   ';DATABASE=sqldb-flexcount-devtwo-ue' + \
                   ';Uid=ce35baab-08f0-4f24-8888-27991566938f' + \
                   ';Pwd=N6w8Q~8G9SJ5su9R-wEH2GR4AB0I_sYw4mHtNaeD' + \
                   ';Authentication=ActiveDirectoryServicePrincipal;Encrypt=yes;MultipleActiveResultSets=False;TrustServerCertificate=no;Connection Timeout=30;'

        db_engine = create_engine(odbc_str)

        llm = AzureChatOpenAI(azure_endpoint="https://oai-fc-devtwo-ue.openai.azure.com/",
                              azure_deployment="GPT-4Turbo",
                              openai_api_version="2024-02-01",
                              api_key="04ff20b86fbe43499f088e3e90cd730a",
                              temperature=0)

        db = SQLDatabase(db_engine, view_support=True)

        sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        sql_toolkit.get_tools()

        sqldb_agent = create_sql_agent(
            llm=llm,
            toolkit=sql_toolkit,
            agent_type="tool-calling",
            verbose=True
        )

        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system",
                 """
                 You are a helpful AI assistant expert in identifying the relevant topic from user's question about 
                     dbo.vw_OnHands_rls and dbo.vw_Inventory_Data_rls view and then querying SQL Database to find answer.
                 Use following context to create the SQL query. Context:
                 dbo.vw_OnHands_rls contains information about on hand inventory Sku's at a particular store for an event 
                     including id_event, sku, description, OnHandQty, price and QtyTolerance.
                 dbo.vw_Inventory_Data_rls contains information about actual counts made during an event 
                     including sku, barcode, quantity, cost, price, department and location_instance. 
                     A single sku value can be found in multiple records in dbo.vw_Inventory_Data_rls. 
 
                 If the question is looking for any sku's with a miscount, using a CTE find total quantity by
                     selecting sku and summing quantity from dbo.vw_Inventory_Data_rls for a particular id_event grouping on sku 
                     taking the CTE results to query dbo.vw_onhands_rls o  where the records in the CTE matches on SKU
                     for the same id_Event including the sku, description, OnHandQty, QtyTolerance, and price fields and the total quantity 
                     result from the CTE as Total Counted showing records that have a difference between OnHandQty and the 
                     sum of quantity from the CTE greater than the the QtyTolerance
 
                 If the question is about number of products with duplicate counts, then using the dbo.vw_Inventory_Data_rls view 
                     find duplicate entries by sku with identical entries for the same id_location_instance and quantity.
                     Results should be filtered by an Event ID (id_event).
                 """
                 ),
                ("user", "{question}\n ai: "),
            ]
        )

        output = sqldb_agent.run(final_prompt.format(
            question=query
            #    question = "Are there any miscounts for event 49?"
        ))
    except Exception as e:
        output = f"exception: {e}"
    return output
