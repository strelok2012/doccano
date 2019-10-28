import numpy as np
import pandas as pd
import seaborn as sns
# import copy
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report
from sklearn.metrics import roc_curve, auc, precision_recall_curve
import matplotlib.pyplot as plt


def plot_roc_curve( y_predict_proba, y_truth):
    y_score = np.array(y_predict_proba)
    if len(y_truth.shape) == 1:
        dummies = pd.get_dummies(y_truth)
        y_dummies = dummies.values
    else:
        y_dummies = y_truth

    y_classes = dummies.columns

    # Compute ROC curve and ROC area for each class
    fpr = dict()
    tpr = dict()
    thresholds = dict()
    roc_auc = dict()
    for i, class_name in enumerate(y_classes):
        fpr[i], tpr[i], thresholds[i] = roc_curve(y_dummies[:, i], y_score[:, i])
        roc_auc[i] = auc(fpr[i], tpr[i])

    # Compute micro-average ROC curve and ROC area
    fpr["micro"], tpr["micro"], _ = roc_curve(y_dummies.ravel(), y_score.ravel())
    roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])

    plt.figure()
    lw = 2
    for i, class_name in enumerate(y_classes):
        plt.plot(fpr[i], tpr[i],
                 lw=lw, label='%s (area = %0.2f)' % (class_name, roc_auc[i]))

    plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver operating characteristic')
    plt.legend(loc="lower right")

    # threshold for positive class
    ax2 = plt.gca().twinx()
    ax2.plot(fpr[1], thresholds[1], markeredgecolor='r', linestyle='dashed', color='r')
    ax2.set_ylabel('Threshold')
    ax2.set_ylim([thresholds[1][-1], thresholds[1][0]])
    ax2.set_xlim([fpr[1][0], fpr[1][-1]])

    # plt.show()
    return plt.gcf()


def plot_precision_recall_curve(  y_predict_proba, y_truth):
    y_score = np.array(y_predict_proba)
    if len(y_truth.shape) == 1:
        dummies = pd.get_dummies(y_truth)
        y_dummies = dummies.values
    else:
        y_dummies = y_truth

    y_classes = dummies.columns
    for i, class_name in enumerate(y_classes):
        precision, recall, thresholds = precision_recall_curve(y_dummies[:, i], y_score[:, i])

        plt.step(recall, precision,
                 label=class_name,
                 lw=2,
                 where='post')

    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.ylim([0.0, 1.05])
    plt.xlim([0.0, 1.0])
    plt.legend(loc="lower left")

    # ax2 = plt.gca().twinx()
    # ax2.plot(recall[1:], thresholds, markeredgecolor='r',linestyle='dashed', color='r')
    # ax2.set_ylabel('Threshold')

    # plt.show()
    return plt.gcf()


def plot_confidence_performance(y_predict, y_predict_proba, y_truth, num_bins=20):
    predicted_probabilities = np.max(y_predict_proba, axis=1)
    is_correct = (y_truth == y_predict)
    ax = sns.regplot(x=predicted_probabilities, y=is_correct, x_bins=num_bins)
    plt.xlabel('Model Confidence')
    plt.ylabel('Average accuracy')
    # plt.show()
    return plt.gcf()
