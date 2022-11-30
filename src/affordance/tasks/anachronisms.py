from ctypes import util
from  utils import gpt3, propose_decomposition, propose_instruction, chunks, get_subset, OpenAIModel, substring_match, search
import datasets
import numpy as np
from tqdm import tqdm
import datasets
import numpy as np
from tqdm import tqdm
import json, pdb
import re
from sequential_interpreter import TopDownVisitorBeta

# Get data
d = datasets.load_dataset('bigbench', 'anachronisms')
inputs = d['validation']['inputs']
labels = d['validation']['targets']
labels = [l[0] for l in labels]
# inputs = [x.split('\n')[0] for x in inputs]
# labels = np.array([int(x[0] == 'Yes') for x in d['train']['targets'] + d['validation']['targets']])

task_description = "Anachronisms: An anachronism is a mistake in chronology, or a person, thing, or event that is out of its proper time. Figure out whether a sentence contains anachronisms or not, and answer 'Yes' or 'No'."

io_pairs = [("President Syngman Rhee sent a letter commending Hugo Chavez's election victory.",
"Yes"),
("The recognition of Christianity as the official religion of both Ethiopia and the Roman Empire within the same decade is notable.",
"Yes"),
("President Woodrow Wilson rallied Americans to support the U.S. joining the International Atomic Energy Agency.",
"Yes"),
("The T. rex was running toward the herd of Wagyu cattle grazing outside.",
"Yes"),
("Sun Tzu dedicated an entire chapter to describing the failure of Babylon.",
"No"),
("Igor Stravinsky's favorite musical piece was the Symphonie Fantastique.",
"No"),
("The Hagia Sophia has seen drastic transformations to its interior from its inception, including becoming a church, a mosque, a museum, and back to a mosque again. ",
"No"),
("Ponce De Leon used a telegram to report his findings to the king.",
"Yes"),
("Jason connected his new TRS80 color computer to the TV and played Pyramid 2000.",
"No"),
("Richard III used LEDs to light his throne room.",
"Yes")]


def exact_match(labels, predictions):
    correct = 0
    count = 0
    for label, predict in zip(labels, predictions):
        if label.lower() == predict.lower():
            correct += 1
        count += 1
    return (1.0*correct)/count


def token_match(labels, predictions):
    correct = 0
    count = 0
    for label, predict in zip(labels, predictions):
        if label.lower() in [p.lower() for p in predict]:
            correct += 1
        count += 1
    return (1.0*correct)/count


def few_shot():
    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=200, quote='---', n=1)
        prompts = ["""President Syngman Rhee sent a letter commending Hugo Chavez's election victory.
Yes
----
The recognition of Christianity as the official religion of both Ethiopia and the Roman Empire within the same decade is notable.
Yes
----
President Woodrow Wilson rallied Americans to support the U.S. joining the International Atomic Energy Agency.
Yes
----
The T. rex was running toward the herd of Wagyu cattle grazing outside.
Yes
----
Sun Tzu dedicated an entire chapter to describing the failure of Babylon.
No
----
Igor Stravinsky's favorite musical piece was the Symphonie Fantastique.
No
----
The Hagia Sophia has seen drastic transformations to its interior from its inception, including becoming a church, a mosque, a museum, and back to a mosque again. 
No
----
Ponce De Leon used a telegram to report his findings to the king.
Yes
----
Jason connected his new TRS80 color computer to the TV and played Pyramid 2000.
No
----
Richard III used LEDs to light his throne room.
Yes
----
%s""" % x for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        for x in tqdm(chunks(inputs, 20)):
            answers.extend(predict(x))
            pdb.set_trace()
        preds = [x.strip() for x in answers]
        perf_array.append(exact_match(labels, preds))
    print("No decomposition Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

# Human Decomp 
def anachronism():
    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=200, quote='---', n=1)
        prompts = ['''Given a sentence and the time periods of each entity in it, tell me if it could have happened or not.
    Sentence: I wrote about shakespeare
    Entities and dates:
    I -> 21st century
    Shakespeare -> 16th century
    Could the sentence be true based on the dates alone: Yes
    ----
    Sentence: Shakespeare wrote about me

    Entities and dates:
    Shakespeare -> 16th century
    I -> 21st century

    Could the sentence be true based on the dates alone: No
    ----
    Sentence: %s''' % x for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 2
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        for x in tqdm(chunks(inputs, 20)):
            answers.extend(predict(x))
        preds = np.array([int(x.endswith('No')) for x in answers])
        perf_array.append((preds == labels).mean())
    print("Human Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

few_shot_cot_prompt = """In these examples, you are given a task description and an input. Break the input down into subtasks in order to solve the task. You can use search functions like Google search in one or more of your substeps, if there in insufficient information. Other functions like arithmetic and logical operations can also be used.  
Description: Choose the option that best answers the question. If the question does not have a known answer, choose "Unknown". 
Input: How many hairs were on Neil Armstrong's head when he landed on the moon?
  choice: Unknown
  choice: Five million
Q1: [search] How many hairs were on Neil Armstrong's head when he landed on the moon? 
#1: 
Apollo 11 (July 16–24, 1969) was the American spaceflight that first landed humans on the Moon. Commander Neil Armstrong and lunar module pilot Buzz Aldri...
Neil Alden Armstrong (August 5, 1930 – August 25, 2012) was an American astronaut and aeronautical engineer who became the first person to walk on the Moon ...
Q2: [subquestion] Does the information help answer the question? There could be no definitive answer because the question is too specific, about personal details not in public record, because the answer is not yet known, or the question is opinion-based.
#2: No. The question is too specific
Q3: [compare] What is the final answer?
Unknown
Q4: [EOQ]
Ans: Unknown
----
Description: An anachronism is a mistake in chronology, or a person, thing, or event that is out of its proper time. Figure out whether a sentence contains anachronisms or not, and answer 'Yes' or 'No'."
Input: President George H. W. Bush called his generals to the Oval Office at the outset of the Gulf War.
Q1: [tag] What are the entities in this sentence?
#1: 
President George H. W. Bush
Gulf War
Q2: [search] When was President George H. W. Bush president?
#2: George H. W. Bush's tenure as the 41st president of the United States began with his inauguration on January 20, 1989, and ended on January 20, 1993.
Q3: [search] When was the Gulf War fought?
#3: The Gulf War[b] was a 1990–1991 armed campaign waged by a 35-country military coalition in response to the Iraqi invasion of Kuwait.
#4: [subquestion] Could these entities have co-existed and interacted based on this information?
Yes. Their time periods intersect.
Q5: [generate answer] Is this an anachronism?
#5: No
Q6: [EOQ]
Ans: No
----
Description: An anachronism is a mistake in chronology, or a person, thing, or event that is out of its proper time. Figure out whether a sentence contains anachronisms or not, and answer 'Yes' or 'No'."
Input: Kurt Cobain starred in the 1980 television show "Twin Peaks".
Q1: [tag] What are the entities in this sentence?
#1: 
Kurt Cobain
"Twin Peaks"
Q2: [search] When did television show "Twin Peaks" air?
#2: Twin Peaks is an American mystery serial drama television series created by Mark Frost and David Lynch. It premiered on ABC on April 8, 1990, and originally ran for two seasons until its cancellation in 1991.
Q3: [search] When did Kurt Cobain live?
#3: Kurt Donald Cobain (February 20, 1967 – c. April 5, 1994) was an American musician, best known as the lead vocalist, guitarist and primary songwriter of the ...
Q4: [subquestion] Could these entities have co-existed and interacted based on this information?
No. Musician  Kurt Cobain could not have starred in Twin Peaks.
Q5: [generate answer] Is this an anachronism?
#5: Yes
Q6: [EOQ]
Ans: Yes
----
Description: Answer questions about Hindu mythology by choosing the option that best answers the question.
Input: In the Mahabharata, Karna is cursed to forget the incantations needed to use which weapon?
  choice: Anjalikastra
  choice: Narayanastra
  choice: Agneyastra
  choice: Brahmastra
Q1: [subquestion] In the Mahabharata, Karna is cursed to forget the incantations needed to use which weapon?
#1: No.
Q2: [search] In the Hindu epic Ramayana, who is the main villain? 
#2: As a result, he cursed Karna, saying that HIS MARTIAL SKILLS, including the use of BRAHMASTRA, would abandon him when he needed them most. Indra, the King of Gods, stung Karna in the form of a bee to get him cursed by Parshuram. Karna walked through the woods in despair, feeling dejected by the curse. A skilled & devoted warrior...
Q3: [compare] Which option is the answer in #3 most similar to?
#3: Brahmastra
Q4: [EOQ]
Ans: Brahmastra
----
Description: Choose the option that best answers the question. If the question does not have a known answer, choose "Unknown". 
Input: Where was Mark Twain born?
  choice: Unknown
  choice: Florida, Missouri
Q1: [search] Where was Mark Twain born?
#1: 
Mark Twain. Samuel Langhorne Clemens was born in Florida, Missouri, and later moved with his family to Hannibal, Missouri, where he grew up.
Q2: [subquestion] Does the information help answer the question? There could be no definitive answer because the question is too specific, about personal details not in public record, because the answer is not yet known, or the question is opinion-based.
#2: Yes. The answer is Florida, Missouri
Q3: [generate answer] What is the final answer?
Florida, Missouri
Q4: [EOQ]
Ans: Florida, Missouri
----
Desciption: %s 
Input: %s
Q1:"""

def few_shot_cot():
    def predict(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=1000, temperature=0.4, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        for x in tqdm(chunks(inputs, 20)):
            x = [ex.replace("\nDoes the preceding sentence contain non-contemporaneous (anachronistic) elements?", "") for ex in x]
            answers.extend(predict("An anachronism is a mistake in chronology, or a person, thing, or event that is out of its proper time. Figure out whether a sentence contains anachronisms or not, and answer 'yes' or 'no'", x))
        preds = [[y.strip() for y in x.split("\n")] for x in answers]
        perf_array.append(token_match(labels, preds))
    print("Few-shot COT performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

def auto_cot(temperature=0.3):
    auto_cot_prompt = ""
    for io_pair in io_pairs[:5]:
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=1000, temperature=0.7, quote='---', n=1)
        prompt = """%s\n"""% task_description + io_pair[0] + \
            """\nThe final answer is either "Yes" or "No".\nA: Let's think step-by-step.\n""" 
        auto_cot_prompt += prompt
        cot = gpt3(prompt)
        auto_cot_prompt += cot[0] + "\n----\n"
        # Add the final answer with special format so evaluation is easier.
    print(auto_cot_prompt)

    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=500, temperature=temperature, quote='---', n=1)
        prompts=[auto_cot_prompt + """%s\n"""%task_description + \
            """%s\nThe final answer is either "Yes" or "No".\nA: Let's think step-by-step.\n"""% (x) for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        for x in tqdm(chunks(inputs, 20)):
            answers.extend(predict(x))
        preds = [x.strip() for x in answers]
        perf_array.append(substring_match(labels, preds))
    print("Auto-CoT Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

def affordance():
    def predict(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=2048, temperature=0.4, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return gpt3(prompts)

    def search_query(answer):
        lines = answer.strip().split("\n")
        new_lines = []
        skip=False
        for line in lines:
            if "[search]" in line:
                query_no = re.search('[0-9]+', line.split()[0]).group(0)
                new_lines.append(line)
                query = line[re.search("\[search\]", line).span(0)[1]:].strip()
                search_snippet = search(query, top_k=1)
                new_lines.append("#%s: "%(query_no) + search_snippet)
                # skip a next line or add #2
                skip=True
            else:
                if skip:
                    skip=False
                    continue
                new_lines.append(line)
        return "\n".join(new_lines)


    def predict_with_affordance(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=2048, temperature=0.4, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        new_answers = []
        for x in tqdm(chunks(inputs, 20)):
            x = [ex.replace("\nDoes the preceding sentence contain non-contemporaneous (anachronistic) elements?", "") for ex in x]
            answers = predict("An anachronism is a mistake in chronology, or a person, thing, or event that is out of its proper time. Figure out whether a sentence contains anachronisms or not, and answer 'yes' or 'no'", x)
            
            # Replace all instances of search with actual search outputs.
            # affordance_inputs = [json.loads(a.strip().split("\n")[1].replace("#1: ", "")) for a in answers]
            affordance_outputs = [search_query(a) for a in answers]
            # Find the last search term and resume execution after that.
            last_questions = [re.findall("Q[0-9]+: \[search\]", a)[-1] for a in affordance_outputs]
            query_nos = [re.search('[0-9]+', question.split()[0]).group(0) for question in last_questions]
            next_questions = [re.search(r"Q%s: "%str(int(q) + 1), a) for q, a in zip(query_nos,affordance_outputs)]
            x = [ex + "\n" + a[:q.span(0)[1]] for ex, a, q in zip(x, affordance_outputs, next_questions)]
            pdb.set_trace()
            new_answers.extend(predict_with_affordance("An anachronism is a mistake in chronology, or a person, thing, or event that is out of its proper time. Figure out whether a sentence contains anachronisms or not, and answer 'yes' or 'no'", x))
        preds = [[y.strip() for y in x.split("\n")] for x in new_answers]
        perf_array.append(token_match(labels, preds))
        print(perf_array)
    print("Few-shot COT performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))


def nl_program(temperature=0.3):
    interpreter = TopDownVisitorBeta()

    def predict(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=1000, temperature=temperature, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return prompts, gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        new_labels = ["Ans: " + label for label in labels]
        for x in tqdm(chunks(inputs, 20)):
            x = [ex.replace("\nDoes the preceding sentence contain non-contemporaneous (anachronistic) elements?", "") for ex in x]
            prompts, answer = predict(task_description, x)
            new_answer  = interpreter.batch_visit(prompts, answer)
            answers.extend(new_answer)
        preds = [x.strip() for x in answers]
        perf_array.append(substring_match(new_labels, preds))
        print(perf_array)
    print("FS-CoT Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

nl_program(temperature=0.3)