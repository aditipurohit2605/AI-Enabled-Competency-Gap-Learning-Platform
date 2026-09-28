"""
Demo Seeding Script for Karmayogi Competency Gap & Learning Platform.

Seeds 25 realistic synthetic Indian learners across the 4 statistical job roles,
complete with synthetic profile bios, self-assessed skills, historical backdated
quiz sessions (over the last 8 weeks), gap snapshots, and 3 pre-loaded training
documents with 12 approved questions each for offline assessments.

Refuses to execute if APP_ENV=production.
Idempotent: Safe to execute repeatedly.
"""

import os
import sys
import random
import datetime
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Production guard
if os.getenv("APP_ENV", "").strip().lower() == "production":
    print("ERROR: backend/seed_demo.py refuses to run when APP_ENV=production.")
    sys.exit(1)

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.competency import Role, Competency, RoleCompetency, UserSkill
from backend.app.models.assessment import Document, Question, QuizSession, QuizAttempt, GapSnapshot
from backend.seed import seed_database as seed_framework_core


# 25 Realistic Indian Learners with MoSPI profiles
LEARNERS_DATA = [
    {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@mospi.gov.in",
        "role_name": "Statistical Assistant",
        "bio": "Statistical assistant with 3 years experience conducting the Periodic Labour Force Survey (PLFS) in northern districts. Hands-on expertise in field data entry, questionnaire verification, and primary data validation.",
        "strengths": ["Statistics Fundamentals", "Survey Design", "Report Writing"],
        "weaknesses": ["Sampling Methods", "SQL"]
    },
    {
        "name": "Priya Patel",
        "email": "priya.patel@mospi.gov.in",
        "role_name": "Statistical Officer",
        "bio": "Statistical officer supervising industrial field operations for the Annual Survey of Industries (ASI). Responsible for district tabular compilations, outlier scrubbing, and monthly progress reports.",
        "strengths": ["Data Cleaning", "Statistics Fundamentals", "Report Writing", "SQL"],
        "weaknesses": ["Machine Learning Basics", "Sampling Methods"]
    },
    {
        "name": "Rajesh Kumar",
        "email": "rajesh.kumar@mospi.gov.in",
        "role_name": "Senior Statistical Officer",
        "bio": "Senior officer coordinating the Index of Industrial Production (IIP) and National Accounts state-level estimates. 8 years evaluating time series indicators, deflators, and sectoral growth rates.",
        "strengths": ["National Accounts Basics", "Regression and Forecasting", "Report Writing"],
        "weaknesses": ["Machine Learning Basics", "Python for Data Analysis"]
    },
    {
        "name": "Sneha Iyer",
        "email": "sneha.iyer@mospi.gov.in",
        "role_name": "Data Scientist",
        "bio": "Data scientist at the Central Statistics Office (CSO) working on automated imputation pipelines, big data integration from GSTN registries, and satellite imagery analysis for crop estimation.",
        "strengths": ["Python for Data Analysis", "SQL", "Data Visualization"],
        "weaknesses": ["Machine Learning Basics", "Sampling Methods"]
    },
    {
        "name": "Vikram Singh",
        "email": "vikram.singh@mospi.gov.in",
        "role_name": "Statistical Assistant",
        "bio": "Field investigator handling household expenditure schedules and Consumer Price Index (CPI) rural basket pricing in Rajasthan. Strong in community interviewing and data entry checks.",
        "strengths": ["Survey Design", "Statistics Fundamentals"],
        "weaknesses": ["Sampling Methods", "Data Cleaning", "SQL"]
    },
    {
        "name": "Ananya Mukherjee",
        "email": "ananya.mukherjee@mospi.gov.in",
        "role_name": "Statistical Officer",
        "bio": "Oversees survey enumerators across eastern state zones. Specialized in survey validation rules and cross-checking sample responses against historical baselines.",
        "strengths": ["Survey Design", "Report Writing", "Data Cleaning"],
        "weaknesses": ["Sampling Methods", "Machine Learning Basics"]
    },
    {
        "name": "Rohan Gupta",
        "email": "rohan.gupta@mospi.gov.in",
        "role_name": "Senior Statistical Officer",
        "bio": "10 years in official statistics focusing on macroeconomic tabulations, GVA by economic activity, and quarterly GDP releases. Experienced in econometric forecasting.",
        "strengths": ["National Accounts Basics", "Regression and Forecasting", "Report Writing"],
        "weaknesses": ["Machine Learning Basics", "Python for Data Analysis"]
    },
    {
        "name": "Pooja Verma",
        "email": "pooja.verma@mospi.gov.in",
        "role_name": "Data Scientist",
        "bio": "Applied statistician building interactive Power BI and Seaborn dashboards for ministerial monitoring. Automating ETL pipelines for administrative data linkage.",
        "strengths": ["Data Visualization", "SQL", "Python for Data Analysis"],
        "weaknesses": ["Sampling Methods", "Machine Learning Basics"]
    },
    {
        "name": "Suresh Reddy",
        "email": "suresh.reddy@mospi.gov.in",
        "role_name": "Statistical Assistant",
        "bio": "Conducts ground data collection for agricultural price indices in Andhra Pradesh. Familiar with tablet-based CAPI interview systems and basic descriptive metrics.",
        "strengths": ["Survey Design", "Statistics Fundamentals"],
        "weaknesses": ["Sampling Methods", "Data Cleaning"]
    },
    {
        "name": "Neha Joshi",
        "email": "neha.joshi@mospi.gov.in",
        "role_name": "Statistical Officer",
        "bio": "State unit supervisor for the Consumer Expenditure Survey. Experienced in sample response tracking, non-response weighting, and discrepancy audits.",
        "strengths": ["Data Cleaning", "Report Writing", "Survey Design"],
        "weaknesses": ["Sampling Methods", "Machine Learning Basics"]
    },
    {
        "name": "Amit Deshmukh",
        "email": "amit.deshmukh@mospi.gov.in",
        "role_name": "Senior Statistical Officer",
        "bio": "Leads the wholesale price analysis division in western zone. Prepares statistical bulletins and monitors commodity basket weighting updates.",
        "strengths": ["Regression and Forecasting", "Statistics Fundamentals", "Report Writing"],
        "weaknesses": ["Machine Learning Basics", "Sampling Methods"]
    },
    {
        "name": "Kavita Nair",
        "email": "kavita.nair@mospi.gov.in",
        "role_name": "Data Scientist",
        "bio": "Predictive modeling specialist working on high-frequency economic activity proxies using electricity consumption and toll transaction logs.",
        "strengths": ["Python for Data Analysis", "SQL", "Data Visualization"],
        "weaknesses": ["Machine Learning Basics", "Sampling Methods"]
    },
    {
        "name": "Rahul Bose",
        "email": "rahul.bose@mospi.gov.in",
        "role_name": "Statistical Assistant",
        "bio": "Junior researcher conducting field audits for urban frame surveys (UFS) and mapping census enumeration blocks in municipal wards.",
        "strengths": ["Survey Design", "Statistics Fundamentals"],
        "weaknesses": ["Sampling Methods", "SQL"]
    },
    {
        "name": "Deepa Rao",
        "email": "deepa.rao@mospi.gov.in",
        "role_name": "Statistical Officer",
        "bio": "Supervises data validation cells in southern regional office. Specializes in statistical error detection and relational database queries.",
        "strengths": ["SQL", "Data Cleaning", "Statistics Fundamentals"],
        "weaknesses": ["Sampling Methods", "Machine Learning Basics"]
    },
    {
        "name": "Manoj Pillai",
        "email": "manoj.pillai@mospi.gov.in",
        "role_name": "Senior Statistical Officer",
        "bio": "National accounts statistician specializing in supply-use tables and financial sector GVA calculations. Regularly collaborates on international statistical harmonizations.",
        "strengths": ["National Accounts Basics", "Report Writing", "Regression and Forecasting"],
        "weaknesses": ["Machine Learning Basics", "Python for Data Analysis"]
    },
    {
        "name": "Swati Kulkarni",
        "email": "swati.kulkarni@mospi.gov.in",
        "role_name": "Data Scientist",
        "bio": "Data analyst skilled in Python, NumPy, and statistical charting. Focused on converting legacy census databases into open-data APIs and reproducible research reports.",
        "strengths": ["Python for Data Analysis", "Data Visualization", "SQL"],
        "weaknesses": ["Sampling Methods", "Machine Learning Basics"]
    },
    {
        "name": "Sanjay Mishra",
        "email": "sanjay.mishra@mospi.gov.in",
        "role_name": "Statistical Assistant",
        "bio": "Enumeration assistant with experience in the All India Survey on Higher Education and district literacy sampling schedules.",
        "strengths": ["Survey Design", "Statistics Fundamentals"],
        "weaknesses": ["Sampling Methods", "Data Cleaning"]
    },
    {
        "name": "Ritu Choudhury",
        "email": "ritu.choudhury@mospi.gov.in",
        "role_name": "Statistical Officer",
        "bio": "Manages regional CPI compilations and oversees local market price data feeds across northeastern states. Experienced in data sanitization protocols.",
        "strengths": ["Data Cleaning", "Report Writing", "Statistics Fundamentals"],
        "weaknesses": ["Sampling Methods", "Machine Learning Basics"]
    },
    {
        "name": "Alok Sengupta",
        "email": "alok.sengupta@mospi.gov.in",
        "role_name": "Senior Statistical Officer",
        "bio": "Econometric modeler focusing on macro forecast sensitivity and inflation expectation tracking. Author of multiple departmental technical monographs.",
        "strengths": ["Regression and Forecasting", "National Accounts Basics", "Report Writing"],
        "weaknesses": ["Machine Learning Basics", "Sampling Methods"]
    },
    {
        "name": "Meera Menon",
        "email": "meera.menon@mospi.gov.in",
        "role_name": "Data Scientist",
        "bio": "Machine learning engineer exploring natural language processing for automated trade classification and Harmonized System (HS) code assignment.",
        "strengths": ["Python for Data Analysis", "SQL", "Data Visualization"],
        "weaknesses": ["Machine Learning Basics", "Sampling Methods"]
    },
    {
        "name": "Gaurav Bhat",
        "email": "gaurav.bhat@mospi.gov.in",
        "role_name": "Statistical Assistant",
        "bio": "Assists with data entry, range checks, and primary cross-tabulations for social consumption and morbidity surveys in Karnataka.",
        "strengths": ["Survey Design", "Statistics Fundamentals"],
        "weaknesses": ["Sampling Methods", "SQL"]
    },
    {
        "name": "Sunita Das",
        "email": "sunita.das@mospi.gov.in",
        "role_name": "Statistical Officer",
        "bio": "Field audit coordinator with 6 years experience inspecting survey data quality and organizing enumerator refresher training clinics.",
        "strengths": ["Survey Design", "Data Cleaning", "Report Writing"],
        "weaknesses": ["Sampling Methods", "Machine Learning Basics"]
    },
    {
        "name": "Nitin Saxena",
        "email": "nitin.saxena@mospi.gov.in",
        "role_name": "Senior Statistical Officer",
        "bio": "Oversees capital formation and investment goods price indexing. Coordinates statistical input tables for policy planning committees.",
        "strengths": ["National Accounts Basics", "Regression and Forecasting", "Report Writing"],
        "weaknesses": ["Machine Learning Basics", "Sampling Methods"]
    },
    {
        "name": "Divya Hegde",
        "email": "divya.hegde@mospi.gov.in",
        "role_name": "Data Scientist",
        "bio": "Specializes in spatial data analytics, GIS-based statistical mapping of economic clusters, and automated geospatial data transformations.",
        "strengths": ["Data Visualization", "Python for Data Analysis", "SQL"],
        "weaknesses": ["Machine Learning Basics", "Sampling Methods"]
    },
    {
        "name": "Harish Chawla",
        "email": "harish.chawla@mospi.gov.in",
        "role_name": "Statistical Assistant",
        "bio": "Conducts survey interviews and data verification for the Unincorporated Non-Agricultural Enterprises survey. Skilled in respondent rapport building.",
        "strengths": ["Survey Design", "Statistics Fundamentals"],
        "weaknesses": ["Sampling Methods", "Data Cleaning"]
    }
]

# 3 Offline Pre-Seeded Documents with 12 MCQs each
DOCUMENTS_DATA = [
    {
        "title": "Sampling Techniques and Frame Design Manual",
        "filename": "demo_sampling_techniques_manual.txt",
        "competency_name": "Sampling Methods",
        "questions": [
            {
                "text": "In stratified random sampling, what is the primary objective of dividing a population into non-overlapping strata?",
                "options": [
                    "To increase the heterogeneity within each individual stratum",
                    "To maximize homogeneity within strata while maximizing variance between strata",
                    "To ensure that all strata have exactly identical sample sizes regardless of population proportion",
                    "To completely eliminate the necessity of maintaining a sampling frame"
                ],
                "correct_index": 1,
                "explanation": "Stratification works best when units within each stratum are as homogeneous as possible, which minimizes within-stratum variance and improves precision.",
                "difficulty": "medium",
                "source_passage": "Stratified random sampling stratifies heterogeneous populations into homogeneous groups. Stratum variance reduction directly increases estimator efficiency."
            },
            {
                "text": "When is cluster sampling preferred over simple random sampling (SRS)?",
                "options": [
                    "When cluster elements are completely homogeneous across the entire population",
                    "When travel costs and geographical dispersion make listing individual units prohibitively expensive",
                    "When the desired margin of error must be zero",
                    "When sampling without replacement cannot be implemented mathematically"
                ],
                "correct_index": 1,
                "explanation": "Cluster sampling reduces logistical and travel costs when the population is widely dispersed across vast geographical areas.",
                "difficulty": "easy",
                "source_passage": "Cluster sampling is chosen primarily for cost effectiveness and operational convenience when a complete listing of population elements is unavailable."
            },
            {
                "text": "What defines the Design Effect (DEFF) in complex survey sampling?",
                "options": [
                    "The ratio of the sample size to the total population size",
                    "The ratio of the variance under the complex design to the variance under simple random sampling of the same size",
                    "The percentage of non-response encountered during field enumeration",
                    "The multiplier applied to correct for surveyor interviewer bias"
                ],
                "correct_index": 1,
                "explanation": "DEFF = Var(complex) / Var(SRS). It quantifies the efficiency gain or loss of a complex design relative to simple random sampling.",
                "difficulty": "hard",
                "source_passage": "The design effect (DEFF) measures the factor by which the variance of an estimator is inflated due to clustering and unequal weighting compared to SRS."
            },
            {
                "text": "In systematic sampling from a population of size N with interval k = N/n, what risk arises if the sampling frame has cyclical periodicity?",
                "options": [
                    "The sample variance will always approach negative values",
                    "The sample may severely over-represent or miss specific cyclical sub-groups, biasing the estimates",
                    "The sample size will automatically double during data collection",
                    "Every unit will possess an identical probability of inclusion"
                ],
                "correct_index": 1,
                "explanation": "If periodicity coincides with the sampling interval k, the sample will draw from the exact same phase of each cycle, creating severe bias.",
                "difficulty": "medium",
                "source_passage": "Periodic ordering within a sampling frame poses a grave hazard in systematic sampling, potentially skewing the sample if the interval k matches the cycle."
            },
            {
                "text": "What does PPS (Probability Proportional to Size) sampling ensure when selecting primary sampling units (PSUs)?",
                "options": [
                    "Larger units have an inversely proportional chance of being drawn",
                    "Units with larger population sizes have a proportionately higher likelihood of selection",
                    "All primary sampling units are selected with equal 1/N probability",
                    "Small units are entirely discarded from the sampling universe"
                ],
                "correct_index": 1,
                "explanation": "Under PPS sampling, larger clusters or villages have selection probabilities directly proportional to their size measure (e.g. population count).",
                "difficulty": "medium",
                "source_passage": "Probability Proportional to Size (PPS) assigns selection likelihood in proportion to auxiliary size measures such as village population or factory output."
            },
            {
                "text": "What is the consequence of applying Neyman allocation in stratified sampling?",
                "options": [
                    "Sample size per stratum is allocated proportional to the product of stratum size and stratum standard deviation",
                    "Every stratum receives an identical sample size regardless of variance",
                    "Stratum standard deviations are assumed to be identical to zero",
                    "Sampling is performed with replacement exclusively"
                ],
                "correct_index": 0,
                "explanation": "Neyman allocation assigns larger sample fractions to strata that are larger and more variable: n_h ∝ N_h * S_h.",
                "difficulty": "hard",
                "source_passage": "Neyman optimal allocation determines sample size per stratum based on the product of stratum weight and stratum variance to minimize total sample variance."
            },
            {
                "text": "Which measure is commonly used to quantify the degree of similarity among units within the same cluster?",
                "options": [
                    "Gini coefficient",
                    "Intraclass correlation coefficient (rho / ICC)",
                    "Kurtosis index",
                    "Shannon entropy"
                ],
                "correct_index": 1,
                "explanation": "The intraclass correlation coefficient (ICC or rho) measures the homogeneity of elements within clusters, determining variance inflation in cluster sampling.",
                "difficulty": "hard",
                "source_passage": "The intraclass correlation coefficient measures internal cluster homogeneity. High positive values increase standard errors in cluster designs."
            },
            {
                "text": "What is an auxiliary variable in survey ratio estimation?",
                "options": [
                    "A variable recorded only when the respondent refuses to answer",
                    "A known benchmark variable correlated with the study variable used to improve estimator precision",
                    "A random noise variable generated by the surveyor",
                    "The unique identifier assigned to an enumerator badge"
                ],
                "correct_index": 1,
                "explanation": "Auxiliary variables with known population totals (such as previous census counts) are used in ratio/regression estimation to reduce variance.",
                "difficulty": "medium",
                "source_passage": "Ratio estimation exploits auxiliary variables X correlated with survey variable Y whose population total is known from administrative registries."
            },
            {
                "text": "What is sampling frame attrition or under-coverage?",
                "options": [
                    "When eligible population elements are omitted from the frame and have zero inclusion probability",
                    "When respondents provide false responses during interview sessions",
                    "When the sample size exceeds the total population count",
                    "When questionnaires are printed on non-standard page sizes"
                ],
                "correct_index": 0,
                "explanation": "Under-coverage happens when target population members are absent from the sampling frame, leading to systematic coverage bias.",
                "difficulty": "easy",
                "source_passage": "Sampling frame defects include under-coverage, duplicate entries, and out-of-scope units. Under-coverage prevents units from having positive inclusion chances."
            },
            {
                "text": "In two-stage cluster sampling, what occurs at the second stage?",
                "options": [
                    "Primary sampling units are selected from the national frame",
                    "Ultimate sampling units (e.g. households) are sampled from the selected primary units",
                    "The survey questions are rewritten by field supervisors",
                    "Data are published directly to media outlets"
                ],
                "correct_index": 1,
                "explanation": "Stage 1 selects PSUs (e.g. villages/blocks); Stage 2 selects Secondary Sampling Units (SSUs, e.g. households) within those selected PSUs.",
                "difficulty": "easy",
                "source_passage": "Two-stage sampling first selects clusters or enumeration blocks, followed by subsampling households or enterprises within those selected clusters."
            },
            {
                "text": "What is the primary role of sampling weights in survey tabulation?",
                "options": [
                    "To assign letter grades to field investigators",
                    "To ensure that each sample unit represents the appropriate number of population units for unbiased totals",
                    "To delete outlier records automatically without supervisor sign-off",
                    "To increase survey processing speed in relational databases"
                ],
                "correct_index": 1,
                "explanation": "The sampling weight (typically the inverse of inclusion probability) scales sample observations to represent their true population proportions.",
                "difficulty": "easy",
                "source_passage": "Base sampling weights equal the reciprocal of selection probability. Non-response adjustment and calibration align survey totals with benchmarks."
            },
            {
                "text": "How does multi-phase (double) sampling differ from multi-stage sampling?",
                "options": [
                    "Multi-phase samples the same units at different levels of detail, while multi-stage samples nested hierarchical units",
                    "Multi-phase sampling can only be conducted during leap years",
                    "Multi-stage sampling does not permit probability sampling techniques",
                    "There is no mathematical distinction between the two concepts"
                ],
                "correct_index": 0,
                "explanation": "In double sampling, a large phase-1 sample gathers basic auxiliary data, and a subsample is queried for detailed metrics. Multi-stage samples clusters within clusters.",
                "difficulty": "hard",
                "source_passage": "Multi-phase sampling gathers preliminary auxiliary variables from an initial large sample before subsampling the same units for in-depth questionnaires."
            }
        ]
    },
    {
        "title": "Applied Machine Learning for Official Statistics",
        "filename": "demo_machine_learning_manual.txt",
        "competency_name": "Machine Learning Basics",
        "questions": [
            {
                "text": "What distinguishes supervised learning from unsupervised learning in statistical modeling?",
                "options": [
                    "Supervised learning requires labeled ground-truth target outputs during training",
                    "Supervised learning can only process text data, not numerical data",
                    "Unsupervised learning requires manual supervisor review for each model prediction",
                    "Supervised learning does not make use of input features"
                ],
                "correct_index": 0,
                "explanation": "Supervised learning algorithms optimize model parameters using labeled input-output pairs (X, y).",
                "difficulty": "easy",
                "source_passage": "Supervised algorithms train on known target vectors y to predict labels for novel feature matrices X. Unsupervised methods discover latent structures without labels."
            },
            {
                "text": "In evaluating classification models with severe class imbalance, why is accuracy a misleading metric?",
                "options": [
                    "Accuracy is mathematically impossible to calculate when class sizes differ",
                    "A naive classifier predicting only the majority class can yield high accuracy while failing to detect the minority class of interest",
                    "Accuracy values can exceed 100% in imbalanced datasets",
                    "Accuracy does not take true negative counts into consideration"
                ],
                "correct_index": 1,
                "explanation": "If 99% of transactions are legitimate, predicting all as legitimate yields 99% accuracy but 0% fraud recall.",
                "difficulty": "medium",
                "source_passage": "Class imbalance severely distorts accuracy. In skewed datasets, metrics like precision, recall, F1-score, and AUC-ROC are essential."
            },
            {
                "text": "What is the primary function of cross-validation in machine learning model development?",
                "options": [
                    "To generate synthetic features from raw strings",
                    "To provide an unbiased estimate of generalization performance on unseen data and mitigate overfitting",
                    "To convert categorical columns into integers",
                    "To encrypt trained weights for secure transmission"
                ],
                "correct_index": 1,
                "explanation": "K-fold cross-validation evaluates model performance across k distinct train-validation splits to prevent overfitting.",
                "difficulty": "medium",
                "source_passage": "K-fold cross-validation partitions training data into k subsets, rotating the validation holdout to evaluate out-of-sample model robustness."
            },
            {
                "text": "How does L1 regularization (Lasso) differ fundamentally from L2 regularization (Ridge)?",
                "options": [
                    "L1 regularization drives coefficients of non-informative features exactly to zero, performing automated feature selection",
                    "L1 regularization squares the weights, while L2 regularization takes their logarithm",
                    "L2 regularization can only be used with decision tree algorithms",
                    "L1 regularization always produces higher training errors than random guessing"
                ],
                "correct_index": 0,
                "explanation": "Lasso penalizes the absolute sum of weights, which forces less relevant feature coefficients directly to zero.",
                "difficulty": "hard",
                "source_passage": "Lasso adds an L1 penalty (|w|) yielding sparse solutions where irrelevant weights become zero, contrasting with Ridge (L2 penalty) which shrinks weights smoothly."
            },
            {
                "text": "What is the bias-variance tradeoff in predictive modeling?",
                "options": [
                    "The balance between underfitting from excessive model simplicity and overfitting from excessive model complexity",
                    "The financial trade-off between purchasing cloud compute vs local GPUs",
                    "The difference between mean absolute error and root mean squared error",
                    "The ratio between training dataset size and testing dataset size"
                ],
                "correct_index": 0,
                "explanation": "High bias leads to underfitting (oversimplified assumptions), while high variance leads to overfitting (capturing dataset noise).",
                "difficulty": "medium",
                "source_passage": "Model error decomposes into bias, variance, and irreducible noise. Overly complex models exhibit high variance; overly constrained models suffer high bias."
            },
            {
                "text": "In a Random Forest ensemble, how are individual decision trees made decorrelated from one another?",
                "options": [
                    "By training each tree on bootstrap sample bags and considering a random subset of features at each split",
                    "By using completely different loss functions for each constituent tree",
                    "By running trees on different operating systems",
                    "By limiting the entire forest to exactly two branches"
                ],
                "correct_index": 0,
                "explanation": "Random Forests combine bootstrap aggregation (bagging) with random feature subspace sampling at split nodes to reduce tree correlation.",
                "difficulty": "medium",
                "source_passage": "Random Forests combine bootstrap aggregating with random feature selection at each node split, decorrelating trees and minimizing overall ensemble variance."
            },
            {
                "text": "Which metric evaluates the harmonic mean of precision and recall?",
                "options": [
                    "Mean Squared Error (MSE)",
                    "F1-Score",
                    "Adjusted R-squared",
                    "Silhouette score"
                ],
                "correct_index": 1,
                "explanation": "F1 = 2 * (Precision * Recall) / (Precision + Recall). It balances false positives and false negatives.",
                "difficulty": "easy",
                "source_passage": "The F1-score balances precision and recall as their harmonic mean, penalizing extreme trade-offs between precision and sensitivity."
            },
            {
                "text": "What is the purpose of one-hot encoding categorical variables for linear models?",
                "options": [
                    "To convert nominal categorical categories into distinct binary indicator columns without imposing an artificial ordinal ranking",
                    "To compress the dataset into fewer bytes on disk",
                    "To sort names alphabetically",
                    "To replace missing values with the column average"
                ],
                "correct_index": 0,
                "explanation": "Nominal categories have no inherent mathematical order. One-hot encoding creates binary indicators to avoid unintended ordering assumptions.",
                "difficulty": "easy",
                "source_passage": "Nominal variables lack mathematical order. One-hot encoding transforms categories into binary indicator vectors for linear estimators."
            },
            {
                "text": "What problem occurs during gradient descent if the learning rate is set excessively high?",
                "options": [
                    "The loss function converges instantaneously to the global minimum",
                    "The algorithm may oscillate wildly or diverge away from the optimal parameter values",
                    "The training data is permanently deleted from disk",
                    "All model weights are automatically normalized between 0 and 1"
                ],
                "correct_index": 1,
                "explanation": "An oversized step size can overshoot the minimum repeatedly, leading to divergence or erratic loss oscillations.",
                "difficulty": "medium",
                "source_passage": "An excessive learning rate causes gradient updates to overshoot the loss surface minimum, resulting in numerical divergence."
            },
            {
                "text": "When deploying machine learning models in public sector applications, why is model interpretability crucial?",
                "options": [
                    "To allow policy officials to audit decision logic, ensure fairness, and explain automated decisions to citizens",
                    "Because black-box models are illegal to execute on modern computers",
                    "Interpretable models run 1,000 times faster in production without exception",
                    "Because interpretability guarantees 100% predictive accuracy"
                ],
                "correct_index": 0,
                "explanation": "Official statistics and public governance require transparent, auditable algorithms that conform to ethical, legal, and equity standards.",
                "difficulty": "easy",
                "source_passage": "Public agency analytics demand auditable explainability (e.g. SHAP, LIME) to safeguard transparency, mitigate bias, and substantiate public policy decisions."
            },
            {
                "text": "In unsupervised learning, what does the Silhouette score evaluate in K-means clustering?",
                "options": [
                    "How close each point in one cluster is to points in neighboring clusters compared to its own cluster",
                    "The percentage of missing values in the feature matrix",
                    "The execution time of the clustering loop in seconds",
                    "The number of duplicate rows in the dataset"
                ],
                "correct_index": 0,
                "explanation": "Silhouette score measures cluster cohesion vs. separation, ranging from -1 (poor clustering) to +1 (dense, well-separated clusters).",
                "difficulty": "hard",
                "source_passage": "The silhouette coefficient assesses clustering quality by contrasting intra-cluster distance against nearest-cluster distance, peaking when clusters are compact and distinct."
            },
            {
                "text": "What is data leakage in predictive modeling pipelines?",
                "options": [
                    "When information from the test/target dataset inadvertently contaminates the training phase, artificially inflating validation metrics",
                    "When hard drive sectors develop hardware read errors",
                    "When database tables are exported to CSV files without encryption",
                    "When a survey enumerator enters responses using an unapproved ballpoint pen"
                ],
                "correct_index": 0,
                "explanation": "Data leakage occurs when features contain future information or test set statistics, producing deceptively optimistic offline results that fail in production.",
                "difficulty": "medium",
                "source_passage": "Data leakage introduces test set artifacts into the training pipeline (e.g. global normalization before train-test split), masking genuine generalization errors."
            }
        ]
    },
    {
        "title": "National Accounts Compilation & Macroeconomic Framework",
        "filename": "demo_national_accounts_manual.txt",
        "competency_name": "National Accounts Basics",
        "questions": [
            {
                "text": "In the System of National Accounts (SNA), what is the fundamental relationship between Gross Value Added (GVA) at basic prices and GDP at market prices?",
                "options": [
                    "GDP at market prices = GVA at basic prices + Product Taxes - Product Subsidies",
                    "GDP at market prices = GVA at basic prices - Product Taxes + Product Subsidies",
                    "GDP at market prices = GVA at basic prices divided by the Consumer Price Index",
                    "GVA and GDP are always identical in every economy"
                ],
                "correct_index": 0,
                "explanation": "GDP at market prices equals GVA at basic prices plus net taxes on products (taxes minus subsidies on products).",
                "difficulty": "medium",
                "source_passage": "Under SNA 2008, GDP at market prices equals GVA at basic prices plus net product taxes (taxes on products minus subsidies on products)."
            },
            {
                "text": "What are the three canonical approaches used to estimate Gross Domestic Product?",
                "options": [
                    "Production (Output) Approach, Expenditure Approach, and Income Approach",
                    "Census Approach, Sample Survey Approach, and Satellite Imagery Approach",
                    "Cash Accounting Approach, Accrual Approach, and Deficit Approach",
                    "Nominal Approach, Real Approach, and Purchasing Power Parity Approach"
                ],
                "correct_index": 0,
                "explanation": "The three classical macroeconomic accounting methods are Production (Output), Expenditure, and Income approaches, which theoretically yield equal totals.",
                "difficulty": "easy",
                "source_passage": "Macroeconomic measurement utilizes three complementary approaches: Production (value added), Expenditure (final use), and Income (factor distribution)."
            },
            {
                "text": "What is Intermediate Consumption in national accounts calculations?",
                "options": [
                    "The value of goods and services consumed as inputs in the production process, excluding fixed asset depreciation",
                    "The money saved by households in commercial banking deposits",
                    "The total value of import duties collected at international seaports",
                    "The salary paid to temporary administrative staff"
                ],
                "correct_index": 0,
                "explanation": "Intermediate consumption consists of goods and services used up or transformed during the production period, subtracted from gross output to yield GVA.",
                "difficulty": "medium",
                "source_passage": "Gross Value Added equals Gross Output minus Intermediate Consumption. Intermediate consumption excludes consumption of fixed capital (depreciation)."
            },
            {
                "text": "How is Real GDP derived from Nominal GDP in macroeconomic accounting?",
                "options": [
                    "By deflating Nominal GDP using the GDP deflator or relevant price indices to remove the effect of inflation",
                    "By adding foreign currency reserves to Nominal GDP",
                    "By multiplying Nominal GDP by the bank lending interest rate",
                    "By subtracting annual government debt repayments from Nominal GDP"
                ],
                "correct_index": 0,
                "explanation": "Real GDP measures physical output volume by valuing current production at constant base-year prices using price deflators.",
                "difficulty": "easy",
                "source_passage": "Nominal GDP measures output at current prices. Real GDP deflates nominal values using price indices to isolate volume changes from inflation."
            },
            {
                "text": "What is the primary function of Supply and Use Tables (SUT) in national accounting?",
                "options": [
                    "To reconcile commodity supply (domestic production + imports) with final and intermediate demand across all economic sectors",
                    "To calculate individual income tax returns for civil servants",
                    "To determine daily foreign exchange trading volumes",
                    "To maintain vehicle registration rosters across provinces"
                ],
                "correct_index": 0,
                "explanation": "SUTs provide an integrated accounting matrix balancing total supply and total use for every product category, serving as the benchmark for GDP compilation.",
                "difficulty": "hard",
                "source_passage": "Supply and Use Tables (SUT) provide a consistent balancing framework reconciling product flows across domestic industries, imports, intermediate consumption, and final demand."
            },
            {
                "text": "Why is double counting a critical hazard in calculating Gross National Product?",
                "options": [
                    "If intermediate goods are counted alongside final goods, total economic output is artificially inflated",
                    "Double counting causes database servers to run out of memory",
                    "It automatically triggers a recession in the following fiscal year",
                    "It leads to negative interest rates across commercial banks"
                ],
                "correct_index": 0,
                "explanation": "Counting the value of flour in wheat and again in bread leads to double-counting. Value added solves this by measuring only new value created at each stage.",
                "difficulty": "easy",
                "source_passage": "To prevent double counting of intermediate transactions, national accounts measure only value added at each production stage or final consumption goods."
            },
            {
                "text": "What constitutes Gross Fixed Capital Formation (GFCF) in national accounts?",
                "options": [
                    "Net acquisitions of produced fixed assets such as machinery, infrastructure, buildings, and intellectual property",
                    "The total stock market market-capitalization of listed corporations",
                    "The net gold bullion reserves held by the central bank",
                    "Total personal cash holdings in circulation"
                ],
                "correct_index": 0,
                "explanation": "GFCF measures additions to fixed tangible and intangible assets (machinery, civil works, software) by producers during the accounting year.",
                "difficulty": "medium",
                "source_passage": "Gross Fixed Capital Formation (GFCF) measures net investments in fixed assets like industrial plants, infrastructure, and software by government and enterprises."
            },
            {
                "text": "In national accounting, what is FISIM (Financial Intermediation Services Indirectly Measured)?",
                "options": [
                    "An indirect measure of bank output derived from the interest rate spread between loans and deposits against a reference rate",
                    "Direct cash fees charged by automated teller machines",
                    "The annual license fee paid by insurance brokers",
                    "The currency minting cost incurred by the central treasury"
                ],
                "correct_index": 0,
                "explanation": "Banks earn margins through interest rate spreads rather than direct explicit fees. FISIM measures this implicit service output.",
                "difficulty": "hard",
                "source_passage": "Financial Intermediation Services Indirectly Measured (FISIM) captures banking output derived from interest rate margins between borrower lending rates and deposit rates."
            },
            {
                "text": "Which component is NOT included in the Expenditure Approach to GDP?",
                "options": [
                    "Compensation of Employees (factor wage share)",
                    "Private Final Consumption Expenditure (PFCE)",
                    "Government Final Consumption Expenditure (GFCE)",
                    "Net Exports (Exports minus Imports)"
                ],
                "correct_index": 0,
                "explanation": "Compensation of Employees is part of the Income Approach, not the Expenditure Approach (which comprises PFCE + GFCE + GFCF + Changes in Stocks + Net Exports).",
                "difficulty": "medium",
                "source_passage": "Expenditure GDP comprises PFCE, GFCE, Gross Capital Formation, and Net Exports. Compensation of employees is measured under the Income Approach."
            },
            {
                "text": "What is the economic definition of the 'Informal Sector' in official statistics?",
                "options": [
                    "Unincorporated household enterprises operating without a separate legal identity and typically not registered with social security registries",
                    "Firms that accept payments via digital UPI QR codes exclusively",
                    "Non-profit organizations registered under charitable trust acts",
                    "Foreign multinational subsidiaries operating in duty-free ports"
                ],
                "correct_index": 0,
                "explanation": "The informal sector comprises unincorporated household enterprises with fewer than a specified threshold of workers, lacking full formal legal documentation.",
                "difficulty": "easy",
                "source_passage": "Informal economy enterprises are unincorporated units owned by households producing goods and services without formal financial balance sheets or commercial registration."
            },
            {
                "text": "What does the base year revision of national accounts accomplish?",
                "options": [
                    "It updates economic weights, price deflators, and structural source data to accurately reflect evolving economic composition",
                    "It resets national currency exchange rates to par with gold",
                    "It cancels all outstanding sovereign debt bonds automatically",
                    "It re-registers all citizen identification numbers"
                ],
                "correct_index": 0,
                "explanation": "Base year revisions incorporate new structural survey data, update price indices, and capture newly emerging industries (e.g. digital services).",
                "difficulty": "medium",
                "source_passage": "Base year rebasing incorporates updated census benchmarks, new industry classifications, and refreshed structural weights to reflect the contemporary economy."
            },
            {
                "text": "In the national accounts identity, how are Net Factor Income from Abroad (NFIA) and Gross National Income (GNI) related?",
                "options": [
                    "Gross National Income (GNI) = Gross Domestic Product (GDP) + Net Factor Income from Abroad (NFIA)",
                    "Gross National Income (GNI) = Gross Domestic Product (GDP) - Net Factor Income from Abroad (NFIA)",
                    "Gross National Income is always zero in open economies",
                    "GNI and GDP are unrelated metrics measured by different ministries"
                ],
                "correct_index": 0,
                "explanation": "GNI equals GDP plus net income received by domestic residents from abroad (wages, investment returns) minus income earned by foreigners domestically.",
                "difficulty": "easy",
                "source_passage": "Gross National Income (GNI) equals GDP plus Net Factor Income from Abroad (NFIA), reflecting income earned by domestic residents regardless of geographic boundary."
            }
        ]
    }
]


def seed_demo_data():
    """Execute complete demo seeding."""
    app = create_app()

    with app.app_context():
        print("\n=======================================================")
        print("[+] Karmayogi Competency Platform - Step 8 Demo Seeder")
        print("=======================================================\n")

        # 1. Ensure core framework (Competencies, Roles, Prerequisites, Courses) is initialized
        print("[1/5] Ensuring foundational competency framework is seeded...")
        seed_framework_core()

        roles_by_name = {r.name: r for r in Role.query.all()}
        comps_by_name = {c.name: c for c in Competency.query.all()}

        # 2. Seed 3 Offline Training Documents & Questions
        print("\n[2/5] Seeding offline training documents and 36 verified MCQs...")
        # Find or create a default demo trainer
        trainer = User.query.filter_by(role="trainer").first()
        if not trainer:
            trainer = User(name="Senior MoSPI Trainer", email="trainer@example.com", password="trainer123", role="trainer")
            db.session.add(trainer)
            db.session.commit()

        for doc_info in DOCUMENTS_DATA:
            comp = comps_by_name.get(doc_info["competency_name"])
            existing_doc = Document.query.filter_by(title=doc_info["title"]).first()
            if not existing_doc:
                doc = Document(
                    title=doc_info["title"],
                    filename=doc_info["filename"],
                    uploaded_by=trainer.id,
                    competency_id=comp.id if comp else None
                )
                db.session.add(doc)
                db.session.commit()
                print(f"  + Added Document: {doc.title}")
            else:
                doc = existing_doc

            # Seed questions for this document
            q_count = 0
            for q_data in doc_info["questions"]:
                existing_q = Question.query.filter_by(document_id=doc.id, text=q_data["text"]).first()
                if not existing_q:
                    q = Question(
                        text=q_data["text"],
                        options=q_data["options"],
                        correct_index=q_data["correct_index"],
                        document_id=doc.id,
                        explanation=q_data["explanation"],
                        source_passage=q_data.get("source_passage"),
                        difficulty=q_data["difficulty"],
                        status="approved"
                    )
                    db.session.add(q)
                    q_count += 1
            if q_count > 0:
                db.session.commit()
                print(f"    - Added {q_count} approved questions for '{doc.title}'")

        # 3. Seed 25 Synthetic Learners
        print("\n[3/5] Seeding 25 synthetic Indian learners across MoSPI roles...")
        now = datetime.datetime.now(datetime.timezone.utc)
        all_comps = list(comps_by_name.values())

        # Ensure learner1 exists
        l1_user = User.query.filter_by(email="learner1@example.com").first()
        if not l1_user:
            l1_user = User(name="Aarav Sharma (Primary Demo)", email="learner1@example.com", password="learner123", role="learner")
            l1_user.target_role_id = roles_by_name.get("Statistical Officer", Role.query.first()).id
            db.session.add(l1_user)
            db.session.commit()

        seeded_learners = []
        for l_data in LEARNERS_DATA:
            target_role = roles_by_name.get(l_data["role_name"], Role.query.first())
            user = User.query.filter_by(email=l_data["email"]).first()
            if not user:
                user = User(
                    name=l_data["name"],
                    email=l_data["email"],
                    password="demo123",
                    role="learner"
                )
                user.target_role_id = target_role.id
                db.session.add(user)
                db.session.commit()
            else:
                user.target_role_id = target_role.id
                db.session.commit()

            seeded_learners.append((user, l_data))

        print(f"  + 25 Learners verified and mapped to roles.")

        # 4. Seed Profile Skills & Historical Assessment Sessions (Uneven Gaps)
        print("\n[4/5] Populating skills, uneven gap distribution, and historical sessions...")
        
        # Sampling Methods and Machine Learning Basics are intentionally weak across the board
        for user, l_data in seeded_learners:
            # Seed profile text skills
            for comp in all_comps:
                # Determine initial level
                if comp.name in l_data["strengths"]:
                    lvl = random.choice([3.0, 4.0])
                elif comp.name in l_data["weaknesses"]:
                    lvl = random.choice([0.0, 1.0])
                elif comp.name in ["Sampling Methods", "Machine Learning Basics"]:
                    lvl = random.choice([0.0, 1.0, 1.0])  # Highly skewed weakness
                else:
                    lvl = random.choice([1.0, 2.0, 2.5])

                existing_skill = UserSkill.query.filter_by(user_id=user.id, competency_id=comp.id).first()
                if not existing_skill:
                    skill = UserSkill(
                        user_id=user.id,
                        competency_id=comp.id,
                        level=lvl,
                        source="self_assessed"
                    )
                    db.session.add(skill)
                else:
                    existing_skill.level = lvl

            db.session.commit()

            # Seed 1 to 3 Historical Quiz Sessions over past 8 weeks
            num_sessions = random.randint(1, 3)

            def get_comp_approved_questions(comp_id):
                doc_ids = [d.id for d in Document.query.filter_by(competency_id=comp_id).all()]
                if not doc_ids:
                    return []
                return Question.query.filter(Question.document_id.in_(doc_ids), Question.status == "approved").all()

            comps_with_questions = [c for c in all_comps if len(get_comp_approved_questions(c.id)) >= 3]
            if not comps_with_questions:
                comps_with_questions = all_comps[:3]

            for s_idx in range(num_sessions):
                chosen_comp = comps_with_questions[s_idx % len(comps_with_questions)]
                # Backdate session
                days_ago = random.randint(3, 50)
                session_time = now - datetime.timedelta(days=days_ago, hours=random.randint(1, 10))

                # If session already exists around this time, skip
                existing_session = QuizSession.query.filter_by(user_id=user.id, competency_id=chosen_comp.id).first()
                if not existing_session:
                    score = random.choice([60.0, 75.0, 80.0, 85.0, 90.0, 95.0])
                    lvl_before = 1.0
                    lvl_after = 2.0 if score >= 70.0 else 1.0

                    q_ids = [q.id for q in get_comp_approved_questions(chosen_comp.id)[:5]]
                    if not q_ids:
                        q_ids = [1, 2, 3]

                    qs = QuizSession(
                        user_id=user.id,
                        competency_id=chosen_comp.id,
                        question_ids=q_ids,
                        started_at=session_time,
                        submitted_at=session_time + datetime.timedelta(minutes=12),
                        score_pct=score,
                        level_before=lvl_before,
                        level_after=lvl_after
                    )
                    db.session.add(qs)
                    db.session.commit()

                    # Add attempts
                    for qid in q_ids:
                        attempt = QuizAttempt(
                            user_id=user.id,
                            session_id=qs.id,
                            question_id=qid,
                            chosen_index=1,
                            is_correct=(score >= 70.0)
                        )
                        db.session.add(attempt)

                    # Also take a GapSnapshot at that timestamp
                    readiness = random.uniform(45.0, 78.0)
                    levels_snapshot = {str(c.id): random.choice([1.0, 2.0, 3.0]) for c in all_comps}
                    snap = GapSnapshot(
                        user_id=user.id,
                        role_id=user.target_role_id or 1,
                        readiness_pct=round(readiness, 1),
                        taken_at=session_time + datetime.timedelta(minutes=15),
                        competency_levels=levels_snapshot
                    )
                    db.session.add(snap)

            db.session.commit()

        print("  + Skills, backdated quiz sessions, and historical trend snapshots created.")

        # 5. Output Demo Access Credentials
        print("\n=======================================================")
        print("[SUCCESS] Demo Data Seeding Complete!")
        print("=======================================================\n")
        print("Platform Roles & Access Credentials:\n")
        print("  1. Administrator:")
        print("     - Email:    admin@example.com")
        print("     - Password: admin123")
        print("     - Access:   Analytics Heatmap, Top Gaps, Framework Manager, User Directory\n")
        print("  2. Trainer:")
        print("     - Email:    trainer@example.com")
        print("     - Password: trainer123")
        print("     - Access:   Document Upload, FAISS Indexing, MCQ Generation, Question Review\n")
        print("  3. Primary Learner:")
        print("     - Email:    learner1@example.com")
        print("     - Password: learner123")
        print("     - Access:   Learner Dashboard, Profile Extraction, Gap Report, Learning Path, Quizzes\n")
        print("  4. Synthetic Demo Learners (Sample):")
        for u, l_data in seeded_learners[:5]:
            print(f"     - {u.name} ({l_data['role_name']}): {u.email} / demo123")
        print("     ... and 20 additional learners populated in executive heatmap matrix.")
        print("\n=======================================================\n")


if __name__ == "__main__":
    seed_demo_data()
