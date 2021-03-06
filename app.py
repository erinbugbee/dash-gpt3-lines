import os
from textwrap import dedent
from turtle import width

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dash import no_update
from dash.dependencies import Input, Output, State
import plotly.express as px
import openai
import pandas as pd
import matplotlib


def Header(name, app):
    title = html.H1(name, style={"margin-top": 5})
    logo = html.Img(
        src=app.get_asset_url("dash-logo.png"), style={"float": "right", "height": 60}
    )
    return dbc.Row([dbc.Col(title, md=8), dbc.Col(logo, md=4)])


# Load data
df = pd.read_csv("data/spaceship_earth.csv")
df = df.rename(columns = {"date": "Date", "datetime": "Date and Time", "SACTMIN": "Actual Wait", "SPOSTMIN": "Posted Wait"})
df = df[df["Posted Wait"] != -999]
df["Ride"] = "Spaceship Earth"
df["Date"] = pd.to_datetime(df["Date"]).dt.date
df["Time"] = pd.to_datetime(df["Date and Time"]).dt.time
df["Year"] = pd.Categorical(pd.to_datetime(df["Date"]).dt.year)
df["Month"] = pd.to_datetime(df["Date"]).dt.month

df_average_month = df.groupby(["Year", "Month"]).mean()
df_average_month["Year"] = df_average_month.index.get_level_values("Year")
df_average_month["Month"] = df_average_month.index.get_level_values("Month")
df_average_month["Ride"] = "Spaceship Earth"


# Authentication
openai.api_key = os.getenv("OPENAI_KEY")


# Define the prompt
prompt = """
Our dataframe "df_average_month" contains the following columns: Ride, Year, Month, Posted Wait, and Actual Wait. 
The wait times are aggregated over the days within a month.


**Description**: The average Posted Wait by month for Spaceship Earth.

**Code**: ```px.line(df_average_month.query("Ride == 'Spaceship Earth'"), x="Month", y="Posted Wait", color = "Year")```
"""

# Create
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

content_style = {"height": "400px"}

chat_input = dbc.InputGroup(
    [
        dbc.Input(
            id="input-text", placeholder="Tell GPT-3 what you want to generate..."
        ),
        dbc.InputGroupAddon(
            dbc.Button("Submit", id="button-submit", color="primary"),
            addon_type="append",
        ),
    ]
)
output_graph = [
    dbc.CardHeader("Graph"),
    dbc.CardImg(
            src="/assets/spaceshipearth.png",
            top=True,
            style={"opacity": 0.8, "height": "500px"},
        ),
        dbc.CardImgOverlay(
            dbc.CardBody(
                [
                dbc.CardBody(dbc.Spinner(dcc.Graph(id="output-graph")), style={"height": "400px"}),
                ],
            ),
        ),]
output_code = [
    dbc.CardHeader("GPT-3 Conversation Interface"),
    dbc.CardBody(
        dbc.Spinner(dcc.Markdown("", id="conversation-interface")),
        style={"height": "725px"},
    ),
]

explanation = f"""
*GPT-3 can generate Plotly graphs from a simple description of what you want, and it
can even modify what you have previously generated!
We can load the Spaceship Earth Wait Times dataset and give the following prompt to GPT-3:*

{prompt}
"""
explanation_card = [
    dbc.CardHeader("What am I looking at?"),
    dbc.CardBody(dcc.Markdown(explanation)),
]

left_col = [dbc.Card(output_graph), html.Br(), dbc.Card(explanation_card)]

right_col = [dbc.Card(output_code), html.Br(), chat_input]

app.layout = dbc.Container(
    [
        Header("Spaceship Earth Wait Times", app),
        html.Hr(),
        dbc.Row([dbc.Col(left_col, md=7), dbc.Col(right_col, md=5)]),
    ],
    fluid=True,
)


@app.callback(
    [
        Output("output-graph", "figure"),
        Output("conversation-interface", "children"),
        Output("input-text", "value"),
    ],
    [Input("button-submit", "n_clicks"), Input("input-text", "n_submit")],
    [State("input-text", "value"), State("conversation-interface", "children")],
)
def generate_graph(n_clicks, n_submit, text, conversation):
    if n_clicks is None and n_submit is None:
        default_fig = px.line(
            df_average_month.query("Ride == 'Spaceship Earth'"),
            x = "Month",
            y = "Posted Wait",
            color = "Year",
        )
        return default_fig, dash.no_update, dash.no_update

    conversation += dedent(
        f"""
    **Description**: {text}

    **Code**:"""
    )

    gpt_input = (prompt + conversation).replace("```", "").replace("**", "")
    print(gpt_input)
    print("-" * 40)

    response = openai.Completion.create(
        engine="davinci",
        prompt=gpt_input,
        max_tokens=200,
        stop=["Description:", "Code:"],
        temperature=0,
        top_p=1,
        n=1,
    )

    output = response.choices[0].text.strip()

    conversation += f" ```{output}```\n"

    try:
        fig = eval(output)
    except Exception as e:
        fig = px.line(title=f"Exception: {e}. Please try again!")

    return fig, conversation, ""


if __name__ == "__main__":
    app.run_server(debug=True)
