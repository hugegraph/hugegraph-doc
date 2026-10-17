---
title: "Query graph data with Hubble Text2GQL"
description: "Ask questions in Hubble, generate and edit Gremlin or Cypher, configure models and prompts, and view query results and execution records."
linkTitle: "Text2GQL Natural-Language Queries"
weight: 3
search_keywords: [Text2GQL, natural-language queries, Gremlin, Cypher, Prompt, Hubble]
---

Enter a question such as “Find up to 5 person vertices” in Text2GQL. Hubble uses the current graph's schema to generate Gremlin or Cypher.
You can view the results directly or edit the statement and run it again. First, follow the
[standalone Hubble guide](/docs/quickstart/toolchain/hugegraph-hubble/) to start the services and confirm that manual queries work on your graph.

- [Run your first query](#first-query) Go from a question to graph results.
- [Choose a model](#models) Use the built-in model or enter a temporary connection.
- [Edit the Prompt](#prompt) Save query rules and examples as shared templates.
{.cards}

## Find your way around

Click an image to enlarge it. These views show where to query, configure models, and find previous queries.

```gallery
![Natural language and graph query results](/docs/images/hubble/text2gql.jpg) # Query workspace
![Gremlin Prompt editor](/docs/images/hubble/text2gql-prompt.jpg) # Prompt templates
![Natural-language execution records](/docs/images/hubble/text2gql-history.jpg) # Execution records
```

## Run your first query {#first-query}

1. Open **Graph Query → GQL Traversal** and check that the graph you want to query is selected at the top.
2. Select **Use built-in model**. If no shared model is available, select **Use temporary model** and enter its connection details.
3. Enter a question in **Natural language**. Gremlin is selected by default; use the language button to switch to Cypher.
4. Click **Generate and run**. The statement appears on the right as it is generated. Once it passes the read-only check, results appear below.
5. Switch between graph, table, and JSON views to check the results. To make changes, edit the statement on the right and click **Run Query**.
{.steps}

![Natural language, editable Gremlin, and graph results](/docs/images/hubble/text2gql.jpg)

> [!TIP]
> Text2GQL uses only the schema your account can read. Generated statements can only read graph data, and edited statements are checked again.
> If the model uses the wrong label or property name, check **Metadata Configuration** and edit the statement, or make your question more specific.

Press <kbd>Ctrl</kbd> / <kbd>Command</kbd> + <kbd>Enter</kbd> to run the action for the focused input.
With focus on the left, it generates and runs a query. With focus on the right, it runs the existing statement.
Drag the divider below the inputs to change both input heights. The divider below the graph adjusts the graph's height.

## Choose a model {#models}

| Entry | When to use it | Where the Key is stored |
| --- | --- | --- |
| Use built-in model | An administrator has configured a shared model | Encrypted in server-side H2, never returned to the browser |
| Use temporary model | You want to use your own model URL, model name, and Key | Current page memory only, cleared on refresh or account changes |

Selecting **Use temporary model** opens the configuration row. You can collapse it when you no longer need it.
Fill in **Temporary API type**, Base URL, and model name. Enter a **Temporary API Key** if the service needs one.
Choose **OpenAI compatible** for OpenAI, DeepSeek, GLM, and similar services, or **Ollama (local)** for local Ollama.
Use a model ID that the service actually provides. A local Ollama service without authentication can leave the Key empty.

The Base URL must be reachable from the **Hubble backend host**. If Hubble runs in a container, `localhost` refers to that container.
Use HTTPS for public model services. Local or private-network services can use HTTP. Enter the Key in its own field, not in the URL.

> [!DETAILS]- What the browser remembers
>
> Temporary API type, URL, and model name are stored per account in `sessionStorage` for the current browser session.
> Successfully used Base URLs and model names also enter that account's `localStorage` recent choices, so you can select them from the input dropdowns.
> These browser records never store Keys.

### Set up a shared model

Administrators can configure a shared model under **System & Operations → Model settings**. Other accounts use the saved configuration.
When Server authentication is disabled, anyone who can access the deployment can change its model settings.

Enter the API type, Base URL, model name, and Key. Enable the model and click **Save and test**.
Hubble saves the settings first, then sends a short request without graph data to check whether the model responds.
If saving succeeds but testing fails, the settings are still saved. Follow the error message to correct them and try again.

**Test saved configuration** tests only the values already saved on the server. Save or discard form changes before using this button.
The saved Key is never displayed. Leave it blank to keep the existing value. Changing the model URL requires a new Key,
except for local Ollama services that do not need one.

![Model settings with the Prompt entry beside the heading](/docs/images/hubble/text2gql-settings.jpg)

> [!DETAILS]- Save and back up the shared Key
>
> Shared settings and Prompts are stored in Hubble's H2 metadata database. Keys are encrypted, with the master key stored in
> `data/text2gql-master.key` by default. Keep a separate copy of this file when backing up H2; without it, saved Keys cannot be decrypted.
> Only the file owner should be able to read it. Keep it in Hubble's data volume so it survives restarts.
> You can also supply a Base64-encoded 32-byte key through `HUBBLE_TEXT2GQL_MASTER_KEY`.

## Edit Text2GQL Prompt {#prompt}

To set query conventions or add generation examples, open **Text2GQL Prompt** beside the **Model settings** heading.
Gremlin and Cypher each have a template. Hubble adds the current graph's schema automatically and sends the question separately,
so you do not need to copy the schema into the template.

1. Select a language and edit its instructions or few-shot examples. Use labels, properties, and relationships that exist in your graph.
2. Click **Apply** to bring the changes back to the model settings form.
3. Save model settings. Subsequent requests will use the new template, and it will remain available after a refresh.
{.steps}

![Large Prompt editor with few-shot examples](/docs/images/hubble/text2gql-prompt.jpg)

**Cancel** discards the current edits in the dialog. **Restore built-in defaults** resets only the active language's draft; you still need to apply and save it.
Built-in and temporary models use the same shared templates. There is no separate Prompt setting on the query page,
and changing a template does not disable the server's read-only checks.

## Async submission and execution records

AI-generated queries can run asynchronously too. Switch the mode on the right to **Async**.
The left button becomes **Generate and submit**, and the right button becomes **Submit Task**.
After submission, click **View task progress** to see the result on the task page. An accepted task can still fail, so check its final status there.
Async execution requires Server's task endpoint for the selected language. Check that support when using Cypher as well.

The footer on the left shows model generation time, including any query correction calls and excluding schema preparation.
The footer on the right shows the time for one query request and response, excluding model generation and graph rendering.
For async records, submission time also excludes the background task's later execution time.
During generation and automatic execution, invalid output or a recognized syntax or schema error can trigger one correction attempt.
Network, authentication, and async submission failures do not trigger another generation.

When you reopen a graph, the inputs restore the latest recorded question and statement for that language, including sync queries and async submissions.
Restoring a record does not run it. If you have started editing, a record that arrives later will not overwrite your input.
Switching between Gremlin and Cypher keeps a separate draft for each language.

The **Natural language** column in execution records helps you find the question you asked. Manual queries without question text show `—`.
Records and favorites expand below the graph. Scroll the browser to see the current page and its pagination controls.

Generation sends the question, current schema, and any necessary correction information to the selected model service. It does not send query results.
Hubble saves questions and executed statements for later reference. Temporary Keys are never written to execution records or H2.

## Troubleshooting

| Problem | What to check first |
| --- | --- |
| Built-in model is unavailable | Ask an authorized user to check that the model is enabled and that its URL and model name are correct |
| Local model cannot connect | Check the Base URL from the Hubble backend host; `localhost` inside a container does not refer to its host |
| Prompt changes disappear after a refresh | Apply changes the form; save model settings to keep the changes |
| Generated statement is rejected or does not run | Check schema names, read-only restrictions, and the query syntax supported by Server |
| Async submission fails | Check the task endpoint and your account's permissions; try the statement in immediate mode first |
