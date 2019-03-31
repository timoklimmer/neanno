# prerequisite:
# download file enron_05_17_2015_with_labels_v2.csv
# from here https://data.world/login?next=%2Fbrianray%2Fenron-email-dataset%2Fworkspace%2Ffile%3Ffilename%3Denron_05_17_2015_with_labels_v2.csv%252Fenron_05_17_2015_with_labels_v2.csv
# and place it into ./samples/enron

#%%
# imports
import numpy as np
import pandas as pd

pd.set_option("display.max_columns", 100)

#%%
# load data
df = pd.read_csv("./samples/enron/enron_05_17_2015_with_labels_v2.csv")
df = df[df.labeled == True]
level1_categories = {
    "1": "Coarse genre",
    "2": "Included/forwarded information",
    "3": "Primary topics",  # if coarse genre 1.1 is selected
    "4": "Emotional tone",  # if not neutral
}
level2_categories = {
    "1.1": "Company Business, Strategy, etc.",
    "1.2": "Purely Personal",
    "1.3": "Personal but in professional context",
    "1.4": "Logistic Arrangements",
    "1.5": "Employment arrangements",
    "1.6": "Document editing/checking",
    "1.7": "Empty message (due to missing attachment)",
    "1.8": "Empty message",
    "2.1": "Includes new text in addition to forwarded material",
    "2.2": "Forwarded email(s) including replies",
    "2.3": "Business letter(s) / document(s)",
    "2.4": "News article(s)",
    "2.5": "Government / academic report(s)",
    "2.6": "Government action(s)",
    "2.7": "Press release(s)",
    "2.8": "Legal documents (complaints, lawsuits, advice)",
    "2.9": "Pointers to url(s)",
    "2.10": "Newsletters",
    "2.11": "Jokes, humor (related to business)",
    "2.12": "Jokes, humor (unrelated to business)",
    "2.13": "Attachment(s) (assumed missing)",
    "3.1": "regulations and regulators (includes price caps)",
    "3.2": "internal projects -- progress and strategy",
    "3.3": "company image -- current",
    "3.4": "company image -- changing / influencing",
    "3.5": "political influence / contributions / contacts",
    "3.6": "california energy crisis / california politics",
    "3.7": "internal company policy",
    "3.8": "internal company operations",
    "3.9": "alliances / partnerships",
    "3.10": "legal advice",
    "3.11": "talking points",
    "3.12": "meeting minutes",
    "3.13": "trip reports",
    "4.1": "jubilation",
    "4.2": "hope / anticipation",
    "4.3": "humor",
    "4.4": "camaraderie",
    "4.5": "admiration",
    "4.6": "gratitude",
    "4.7": "friendship / affection",
    "4.8": "sympathy / support",
    "4.9": "sarcasm",
    "4.10": "secrecy / confidentiality",
    "4.11": "worry / anxiety",
    "4.12": "concern",
    "4.13": "competitiveness / aggressiveness",
    "4.14": "triumph / gloating",
    "4.15": "pride",
    "4.16": "anger / agitation",
    "4.17": "sadness / despair",
    "4.18": "shame",
    "4.19": "dislike / scorn",
}

#%%
def get_top_category(row):
    # note: chooses an arbitrary top category if multiple have the top weight
    level_1_column_index_of_max_weight_category = (
        15
        + np.nanargmax(
            [
                row["Cat_1_weight"],
                row["Cat_2_weight"],
                row["Cat_3_weight"],
                row["Cat_4_weight"],
                row["Cat_5_weight"],
                row["Cat_6_weight"],
                row["Cat_7_weight"],
                row["Cat_8_weight"],
                row["Cat_9_weight"],
                row["Cat_10_weight"],
                row["Cat_11_weight"],
                row["Cat_12_weight"],
            ]
        )
        * 3
    )
    level_2_column_index_of_max_weight_category = (
        level_1_column_index_of_max_weight_category + 1
    )
    top_category_code = (
        str(int(row.iloc[level_1_column_index_of_max_weight_category]))
        + "."
        + str(int(row.iloc[level_2_column_index_of_max_weight_category]))
    )
    top_category = level2_categories[top_category_code]
    return top_category


def get_categories(row):
    categories_list = []
    for i in range(1, 12):
        if pd.notna(row["Cat_{}_weight".format(i)]):
            category_code = (
                str(int(row["Cat_{}_level_1".format(i)]))
                + "."
                + str(int(row["Cat_{}_level_2".format(i)]))
            )
            category = level2_categories[category_code]
            categories_list.append(category)
    return "|".join(categories_list)


df["top_category"] = df.apply(lambda row: get_top_category(row), axis=1)
df["categories"] = df.apply(lambda row: get_categories(row), axis=1)

#%%
df.to_csv('./samples/enron/emails.csv', header=True, index=False)

#%%
df = pd.read_csv('./samples/enron/emails.csv')
df.head()