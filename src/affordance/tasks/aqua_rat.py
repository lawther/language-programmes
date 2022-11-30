from re import L
from turtle import pd
from utils import gpt3, propose_decomposition, propose_instruction, chunks, get_subset, OpenAIModel, cache_dir, substring_match

import datasets
import numpy as np
from tqdm import tqdm
import json, pdb
import re

data = datasets.load_dataset('aqua_rat', 'raw', cache_dir=cache_dir)['validation']
inputs = [d['question'] + " " + " ".join(d['options']) for d in data]
labels = [d['correct'] for d in data]
print(len(inputs))

task_description="Answer the following multiple-choice arithmetic reasoning problems, choosing one of the five options as the final answer."

io_pairs = [
("""What is the sum of 100 consecutive integers from -49 inclusive, in a increasing order? A)-29 B)50 C)-30 D)30 E)60""",
"50"),
("""A box contains nine bulbs out of which 4 are defective. If four bulbs are chosen at random, find the probability that atleast one bulb is good? A)125/128 B)125/120 C)125/126 D)125/125 E)125/121""",
"125/126"),
("""Four of the five parts numbered (a), (b), (c), (d) and (e) are exactly equal. Which of the parts is not equal to the other four? The number of that part is the answer. A)16.80 × 4.50 + 4.4 B)1600 ÷ 40 + 16 × 2.5 C)5.5 × 8.4 + 34.6 D)1620 ÷ 20 – 1 E)1856.95 – 1680.65 – 96.3""",
"5.5 × 8.4 + 34.6"),
("""An investment of $3000 was made in a certain account and earned interest that was compounded annually. The annual interest rate was fixed for the duration of the investment, and after 12 years the $3000 increased to $12000 by earning interest. In how many years after the initial investment was made the $3000 have increased to $24000 by earning interest at that rate? A)16 B)22 C)20 D)18 E)30""",
"18"),
("""Ramu bought an old car for Rs. 42000. He spent Rs. 13000 on repairs and sold it for Rs. 64900. What is his profit percent? A)16%% B)88%% C)18%% D)14%% E)28%%""",
"18%%"),
("""C and D started a business investing Rs. 49,000 and Rs. 35,000 respectively. In what ratio the profit earned after 4 years be divided between C and D respectively? A)7:4 B)7:5 C)6:4 D)5:5 E)None of these""",
"7:5"),
("""What is the area M of the square with the following coordinates: (x, y), (20, 20), (20, 5), (x, 5)? A)60. B)85. C)125. D)225. E)It cannot be determined from the information given""",
"225"),
("""Shobha's Mathematics Test had 75 problems i.e. 10 arithmetic, 30 algebra and 35 geometry problems. Although she answered 70%% of the arithmetic, 40%% of the algebra and 60%% 0f the geometry problems correctly, she did not pass the test because she got less than 60%% of the problems right. How many more questions she would have needed to answer correctly to earn a 60%% passing grade? A)5 B)10 C)15 D)20 E)25""",
"5"),
("""If a, b, and c are consecutive even integers and a < b < c, all of the following must be divisible by 4 EXCEPT A)a + c B)b + c C)ac D)(bc)/2 E)(abc)/4""",
"b + c"),
("""Two trains, each 160 m long, moving in opposite directions, cross other in 8 sec. If one is moving twice as fast the other, then the speed of the faster train is? A)26 km/hr B)17 km/hr C)60 km/hr D)77 km/hr E)96 km/hr""",
"96 km/hr"),
]

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


def aqua_rat():
    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=200, quote='---', n=1)
        prompts = ["""What is the sum of 100 consecutive integers from -49 inclusive, in a increasing order? A)-29 B)50 C)-30 D)30 E)60
B
----
A box contains nine bulbs out of which 4 are defective. If four bulbs are chosen at random, find the probability that atleast one bulb is good? A)125/128 B)125/120 C)125/126 D)125/125 E)125/121
C
----
Four of the five parts numbered (a), (b), (c), (d) and (e) are exactly equal. Which of the parts is not equal to the other four? The number of that part is the answer. A)16.80 × 4.50 + 4.4 B)1600 ÷ 40 + 16 × 2.5 C)5.5 × 8.4 + 34.6 D)1620 ÷ 20 – 1 E)1856.95 – 1680.65 – 96.3
C
----
An investment of $3000 was made in a certain account and earned interest that was compounded annually. The annual interest rate was fixed for the duration of the investment, and after 12 years the $3000 increased to $12000 by earning interest. In how many years after the initial investment was made the $3000 have increased to $24000 by earning interest at that rate? A)16 B)22 C)20 D)18 E)30
D
----
Ramu bought an old car for Rs. 42000. He spent Rs. 13000 on repairs and sold it for Rs. 64900. What is his profit percent? A)16%% B)88%% C)18%% D)14%% E)28%%
C
----
C and D started a business investing Rs. 49,000 and Rs. 35,000 respectively. In what ratio the profit earned after 4 years be divided between C and D respectively? A)7:4 B)7:5 C)6:4 D)5:5 E)None of these
B
----
What is the area M of the square with the following coordinates: (x, y), (20, 20), (20, 5), (x, 5)? A)60. B)85. C)125. D)225. E)It cannot be determined from the information given
D
----
Shobha's Mathematics Test had 75 problems i.e. 10 arithmetic, 30 algebra and 35 geometry problems. Although she answered 70%% of the arithmetic, 40%% of the algebra and 60%% 0f the geometry problems correctly, she did not pass the test because she got less than 60%% of the problems right. How many more questions she would have needed to answer correctly to earn a 60%% passing grade? A)5 B)10 C)15 D)20 E)25
A
----
If a, b, and c are consecutive even integers and a < b < c, all of the following must be divisible by 4 EXCEPT A)a + c B)b + c C)ac D)(bc)/2 E)(abc)/4
B
----
Two trains, each 160 m long, moving in opposite directions, cross other in 8 sec. If one is moving twice as fast the other, then the speed of the faster train is? A)26 km/hr B)17 km/hr C)60 km/hr D)77 km/hr E)96 km/hr
E
----
%s
""" % x for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        for x in tqdm(chunks(inputs, 20)):
            answers.extend(predict(x))
        preds = [x.strip() for x in answers]
        perf_array.append(exact_match(labels, preds))
    print("No decomposition Performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))

def auto_cot(temperature=0.3):
    auto_cot_prompt = ""
    for io_pair in io_pairs[:5]:
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=1000, temperature=0.7, quote='---', n=1)
        prompt = """%s\n"""% task_description + io_pair[0] + \
            """\nThe final answer one of the five options.\nA: Let's think step-by-step.\n""" 
        auto_cot_prompt += prompt
        cot = gpt3(prompt)
        auto_cot_prompt += cot[0] + "\n----\n"
        # Add the final answer with special format so evaluation is easier.
    print(auto_cot_prompt)

    def predict(chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=500, temperature=temperature, quote='---', n=1)
        prompts=[auto_cot_prompt + """%s\n"""%task_description + \
            """%s\nThe final answer one of the five options.\nA: Let's think step-by-step.\n"""% (x) for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        label_dict = ["ABCDE".index(l) for l in labels]
        new_labels = [re.split('[ABCDE]\)', inp[re.search("A\)", inp).span(0)[0]:])[1:][label_dict[i]] for i, inp in enumerate(inputs)]
        for x in tqdm(chunks(inputs, 20)):
            # x = [ex.replace("\nA:", "") for ex in x]
            answers.extend(predict(x))
        preds = [x.strip() for x in answers]
        perf_array.append(substring_match(new_labels, preds))
    print("Auto-CoT Performance:")
    print("Perf Array", perf_array)
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))


few_shot_cot_prompt="""In these examples, you are given a task description and an input. Break the input down into subtasks in order to solve the task. You can use arithmetic and algebra functions in one or more of your substeps.
Description: Solve the following arithmetic problems on ratios and fractions, , writing out intermediate arithmetic calculations as needed.
Input: Divide the number 49 into two parts, such that if the greater part is increased by 6 and the lesser part is decreased by 11, their ratio is 9 to 2. What is the greater number?
    choice: 29 
    choice: 30 
    choice: 31 
    choice: 32 
    choice: None
Q1: [algebra] Let the greater part be x. What is the lesser part?
#1: 49-x
Q2: [algebra] What is the greater part if increased by 6
#2: x+6
Q2: [algebra] What is the lesser part if decreased by 11
#2: 49-x-11
Q3: [algebra] What is the ratio of greater to lesser after the change?
#3: (x+6):(49-x-11)
Q4: [algebra] Write down the equation to solve for x
#4: (x+6):(49-x-11) = 9:2
Q5: [solve] Solve for x: (x+6):(49-x-11) = 9:2
#5: x = 30
Q6: [compare] Which option is closes to this answer?
#6: 30
Q7: [EOC]
30
----
Description: Find the date based on provided information.
Input: Today is the last day of the first quarter of 2008. What is the date one week from today in MM/DD/YYYY?
Q1: [search] What is the first quarter of a year?
#1: The traditional calendar quarters that make up the year are: Dates for Q1: January 1 – March 31. Dates for Q2: April 1 – June 3. Dates for Q3: July 1 – September 30. Dates for Q4: October 1 – December 31.
Q2: [arithmetic] What is the last day of the first quarter?
#2: March 31
Q3: [arithmetic] What day is today?  
#3: March 31, 2008
Q4: [string reformat] March 31, 2008
#4: 03/31/2008
Q5: [arithmetic] What is 1 week from today?
#5: 04/07/2008
Q6: [EOC]
04/07/2008
----
Description: Solve the following arithmetic word problems, writing out intermediate arithmetic calculations as needed.
Input: A toy manufacturer receives an order for 400 toys. 5 workers are available to work on the order. 2 of the workers produce 6 toys an hour, and another 2 workers produce 4 toys an hour. They all work on the order during their 10-hour shift, and by the end of their shift the manufacturer still needs another 20 toys to be able to ship the order. How many toys per hour does the fifth worker produce?
Q1: What is total number of toys that need to be made?
#1: 400
Q2: How many workers in total?
#2: 5
Q3: [arithmetic] How many toys do 2 of the workers produce?
#3: 2 workers working for 10 hours making 6 toys per hour produce 2*10*6 = 120 toys.
Q4: [arithmetic] How many toys do another 2 of workers produce?
#4: 2 workers working for 10 hours making 4 toys per hour produce 2*10*4 = 80 toys.
Q5: [arithmetic] How many toys did the last worker make?
#5: Out of 400 toys, 120+80=200 toys were made by the first 4 workers. The 5th worker didn't finish the job, since 20 toys were still remaining to be made. So they made 400-200-20=180 toys.
Q6: [arithmetic] How many toys per hour does the fifth worker produce if he worked for 10 hours?
#6: The 5th worker made 180/10 = 18 toys per hour.
Q7: [EOC]
18
----
Description: What is the result of the following arithmetic operations? Write out intermediate arithmetic calculations as needed.
Input: add 70 to 90, subtract 20 from result, subtract result from 200.
 choice:130
 choice:80
 choice:150
 choice:100
 choice:60
Q1: [arithmetic] add 70 to 90
#1: 70+90=160
Q2: [arithmetic] subtract 20 from 160
#2: 160-20=140
Q3: [arithmetic] subtract result 140 from 200
#3: 200-140=60
Q4: [compare] Which option does the final answer match?
#4: 60
Q5: [EOC]
60
----
Description: Solve the following arithmetic word problems, writing out intermediate arithmetic calculations as needed.
Input: Viola had 167 Bread. Nancy took 137 from him. Now How many Bread Viola have difference?
Q1: [arithmetic] How much bread does Viola have if he had 167 loafs before and Nancy too 137 of them?
#1: 167-137=30
Q2: [EOC]
30
----
Description: Determine if following the given navigation instructions, you return to the starting point. If yes, say "Yes", otherwise, say "No"
Input: Take 7 steps. Turn right. Take 8 steps. Turn around.
Q1: Does this question require vector arithmetic?
#1: Yes.
Q2: [subquestion] Which way are you facing when you start? If unknown, assume you face forward?
#2: Face forward
Q3: [subquestion] What is the distance moved forward?
#3: 7 steps
Q4: [subquestion] What is the distance moved right?
#4: 8 steps
Q5: [subquestion] What is the distance moved backward?
#5: 0 steps
Q6: [subquestion] What is the distance moved left?
#6: 0 steps
Q7: [arithmetic] What is total distance moved from starting point?
#7: 7 steps vertically, 8 steps horizontally 
Q8: [subquestion] Is the total distance moved, both vertically and horizontally, 0? 
#8: No
Q9: [EOC]
No
----
Description: 
Input: If two trains depart from a station in opposite directions, and one train is traveling 60 miles an hour while the other is traveling half that distance per hour, how far apart are they from each other after 3 hours?
Q1: [arithmetic] What is the speed of the second train? 
#1: 60/2=30 miles an hour
Q2: [arithmetic] What is distance travelled by first train?
#2: 60*3=180 miles
Q3: [arithmetic] What is distance travelled by first train?
#3: 30*3=90 miles
Q4: [subquestion] Are the trains moving towards or away from each other?
#4: Away from each other.
Q5: [arithmetic] How far apart are the trains after 3 hours?
#5: 180+90=270 miles
Q6: [EOC]
270 miles
----
Desciption: %s
Input: %s
Q1: """

def few_shot_cot(temperature=0.3):
    def predict(description, chunk):
        gpt3 = OpenAIModel(model="text-davinci-002",  max_length=1024, temperature=temperature, quote='---', n=1)
        prompts=[few_shot_cot_prompt% (description, x) for x in chunk]
        return gpt3(prompts)

    perf_array = []
    runs = 5
    for run in range(runs): 
        print("Run %d"%run)
        answers = []
        label_dict = ["ABCDE".index(l) for l in labels]
        new_labels = [re.split('[ABCDE]\)', inp[re.search("A\)", inp).span(0)[0]:])[1:][label_dict[i]].strip() for i, inp in enumerate(inputs)]
        for x in tqdm(chunks(inputs, 20)):
            x = [ex.replace("\nA:", "") for ex in x]
            answers.extend(predict(task_description, x))
        # preds = [[y.strip() for y in x.split("\n")] for x in answers]
        preds = [x.strip() for x in answers]
        perf_array.append(substring_match(new_labels, preds))
        print(perf_array)
    print("FS-CoT performance:")
    print("Mean", np.mean(perf_array))
    print("Std. Dev", np.std(perf_array))


few_shot_cot(temperature=0.3)
