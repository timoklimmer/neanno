import pandas as pd
from flashtext import KeywordProcessor
keyword_processor = KeywordProcessor()

df = pd.DataFrame({"Term": ["PM", "AI"], "EntityCode": ["Role", "Subject"]})
df["ReplaceAgainst"] = '(' + df["Term"] + '| ' + df["EntityCode"] + ')'
df = df.drop(columns=["EntityCode"])

print(df)

keyword_dict = df.set_index('ReplaceAgainst').T.to_dict('list')
#keyword_dict = df.to_dict('list')

print(keyword_dict)

keyword_processor.add_keywords_from_dict(keyword_dict)

new_sentence = keyword_processor.replace_keywords('I am one of the PM for AI.')
print(new_sentence)