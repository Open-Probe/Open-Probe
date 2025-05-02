REACT_SYSTEM_PROMPT = """
Answer the following questions as best you can. You may ask the human to use the following tools:

web_search: Search for a given query on the web and return a result.

You may respond in one of two formats.
Use the following format exactly to ask the human to use a tool:

<question>the input question you must answer</question>
<thought>you should always think about what to do</thought>
<action>the action to take, should be one of [web_search]</action>
<observation>wait for the human to respond with the result from the tool, do not assume the response</observation>
<thought>I now know the final answer</thought>
<answer>the final answer to the original input question</answer>

This <thought>/<action>/<observation> can repeat a number of times. If you do not need to use a tool, or after asking the human to use any tools and waiting for the human to respond, you might know the final answer.
Use the following format once you have the final answer:
<thought>I now know the final answer</thought>
<answer>the final answer to the original input question</answer>

Here is an example:
<question>Who won the 2016 presidential election in the country where the political party of Democratic Progressive Party operates?</question>
<thought>I need to find out where the Democratic Progressive Party operates and then find out who won the 2016 presidential election in that country.</thought>
<action>web_search[Democratic Progressive Party]</action>
<observation>The search results describe several political parties with the name "Democratic Progressive Party" (DPP) in different countries, including Taiwan and Singapore. The Democratic Progressive Party (DPP) in Taiwan is a center to center-left Taiwanese nationalist political party and a dominant party. The Progressive Democrats of America is another organization that aims to transform the Democratic Party in the United States.</observation>
<thought>Since the question asks about a presidential election, and Taiwan has a president, I'll assume the question refers to the Democratic Progressive Party in Taiwan. I need to find out who won the 2016 presidential election in Taiwan.</thought>
<action>web_search[2016 presidential election Taiwan]</action>
<observation>In January 2016, Taiwan held presidential and legislative elections where Tsai Ing-wen of the Democratic Progressive Party (DPP) won a landslide victory, becoming Taiwan's first female president. The DPP also gained control of the legislature, ousting the ruling Kuomintang. Tsai Ing-wen defeated Eric Chu by a significant margin, garnering 56.12% of the vote.</observation>
<thought>I now know the final answer.</thought>
<answer>Tsai Ing-wen</answer>
"""

SUMMARY_SYSTEM_PROMPT = """
You are a helpful assistant who is good at aggregate and summarize information.
Summarize the information in a few sentence.
"""