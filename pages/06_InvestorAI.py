from langchain.schema import SystemMessage
import streamlit as st
import os
import requests
from typing import Type
from langchain.chat_models import ChatOpenAI
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from langchain.agents import initialize_agent, AgentType
from langchain.utilities import DuckDuckGoSearchAPIWrapper

llm = ChatOpenAI(temperature=0.1, model_name="gpt-3.5-turbo-1106")

alpha_vantage_api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")

class StockMarketSymbolSearchToolArgsSchema(BaseModel):
    query: str = Field(
        description="The query you will search for. Example query: Stock Market Symbol for Apple Company"
    )

class StockMarketSymbolSearchTool(BaseTool):
    name = "StockMarketSymbolSearchTool"
    description = """
    Use this tool to find the stock market symbol for a company.
    It takes a query as an argument.
    """
    args_schema: Type[StockMarketSymbolSearchToolArgsSchema] = StockMarketSymbolSearchToolArgsSchema

    def _run(self, query):
        ddg = DuckDuckGoSearchAPIWrapper()
        try:
            result = ddg.run(query)
            print(f"StockMarketSymbolSearchTool query: {query}")
            print(f"StockMarketSymbolSearchTool result: {result}")
            return result
        except Exception as e:
            error_message = f"An error occurred while searching for the stock symbol: {e}"
            print(error_message)
            return error_message

class CompanyOverviewArgsSchema(BaseModel):
    symbol: str = Field(
        description="Stock symbol of the company. Example: AAPL, TSLA",
    )

class CompanyOverviewTool(BaseTool):
    name = "CompanyOverview"
    description = """
    Use this to get an overview of the financials of the company.
    You should enter a stock symbol.
    """
    args_schema: Type[CompanyOverviewArgsSchema] = CompanyOverviewArgsSchema

    def _run(self, symbol):
        try:
            r = requests.get(
                f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={alpha_vantage_api_key}"
            )
            r.raise_for_status()
            result = r.json()
            print(f"CompanyOverviewTool symbol: {symbol}")
            print(f"CompanyOverviewTool result: {result}")
            return result
        except requests.exceptions.RequestException as e:
            error_message = f"An error occurred while fetching the company overview: {e}"
            print(error_message)
            return error_message

class CompanyIncomeStatementTool(BaseTool):
    name = "CompanyIncomeStatement"
    description = """
    Use this to get the income statement of a company.
    You should enter a stock symbol.
    """
    args_schema: Type[CompanyOverviewArgsSchema] = CompanyOverviewArgsSchema

    def _run(self, symbol):
        try:
            r = requests.get(
                f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={symbol}&apikey={alpha_vantage_api_key}"
            )
            r.raise_for_status()
            result = r.json().get("annualReports", "No data found")
            print(f"CompanyIncomeStatementTool symbol: {symbol}")
            print(f"CompanyIncomeStatementTool result: {result}")
            return result
        except requests.exceptions.RequestException as e:
            error_message = f"An error occurred while fetching the income statement: {e}"
            print(error_message)
            return error_message

class CompanyStockPerformanceTool(BaseTool):
    name = "CompanyStockPerformance"
    description = """
    Use this to get the weekly performance of a company stock.
    You should enter a stock symbol.
    """
    args_schema: Type[CompanyOverviewArgsSchema] = CompanyOverviewArgsSchema

    def _run(self, symbol):
        try:
            r = requests.get(
                f"https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={symbol}&apikey={alpha_vantage_api_key}"
            )
            r.raise_for_status()
            response = r.json()
            result = list(response.get("Weekly Time Series", {}).items())[:200]
            print(f"CompanyStockPerformanceTool symbol: {symbol}")
            print(f"CompanyStockPerformanceTool result: {result}")
            return result
        except requests.exceptions.RequestException as e:
            error_message = f"An error occurred while fetching the stock performance: {e}"
            print(error_message)
            return error_message

agent = initialize_agent(
    llm=llm,
    verbose=True,
    agent=AgentType.OPENAI_FUNCTIONS,
    handle_parsing_errors=True,
    tools=[
        CompanyIncomeStatementTool(),
        CompanyStockPerformanceTool(),
        StockMarketSymbolSearchTool(),
        CompanyOverviewTool(),
    ],
    agent_kwargs={
        "system_message": SystemMessage(
            content="""
            You are a hedge fund manager.
            
            You evaluate a company and provide your opinion and reasons why the stock is a buy or not.
            
            Consider the performance of a stock, the company overview and the income statement.
            
            Be assertive in your judgement and recommend the stock or advise the user against it.
        """
        )
    },
)

st.set_page_config(
    page_title="InvestorGPT",
    page_icon="💼",
)

st.markdown(
    """
    # InvestorAI
            
    Welcome to InvestorGPT.
            
    Write down the name of a NASDAQ company and our Agent will do the research for you.
"""
)

company = st.text_input("Write the name of the company you are interested in.")

if company:
    print(f"User input: {company}")
    result = agent.invoke(company)
    print(f"Agent result: {result}")
    st.write(result["output"].replace("$", "\$"))
