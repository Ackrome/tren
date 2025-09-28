import numpy as np
import torch
import torch.nn as nn

n_actions = 2

def to_one_hot(y_tensor, ndims):
    """ helper: take an integer vector and convert it to 1-hot matrix. """
    y_tensor = y_tensor.type(torch.LongTensor).view(-1, 1)
    y_one_hot = torch.zeros(
        y_tensor.size()[0], ndims).scatter_(1, y_tensor, 1)
    return y_one_hot


def predict_probs(states, model):
    """
    Predict action probabilities given states.
    :param states: numpy array of shape [batch, state_shape]
    :param model: torch model
    :returns: numpy array of shape [batch, n_actions]
    """
    # convert states, compute logits, use softmax to get probability

    states_tensor = torch.tensor(states, dtype=torch.float32)
    
    with torch.no_grad():
        logits = model(states_tensor)
        probs = nn.functional.softmax(logits, dim=-1).numpy()
    
    # probs = None
    assert probs is not None, "probs is not defined"

    return probs

def get_cumulative_rewards(rewards,  # rewards at each step
                           gamma=0.99  # discount for reward
                           ):
    """
    Take a list of immediate rewards r(s,a) for the whole session
    and compute cumulative returns (a.k.a. G(s,a) in Sutton '16).

    G_t = r_t + gamma*r_{t+1} + gamma^2*r_{t+2} + ...

    A simple way to compute cumulative rewards is to iterate from the last
    to the first timestep and compute G_t = r_t + gamma*G_{t+1} recurrently

    You must return an array/list of cumulative rewards with as many elements as in the initial rewards.
    """
    # YOUR CODE GOES HERE
    cumulative_rewards = np.zeros_like(rewards, dtype=float)
    G_next = 0
    for t in reversed(range(len(rewards))):
        G_cur = rewards[t]  + gamma*G_next
        cumulative_rewards[t] = G_cur
        G_next = G_cur
    assert cumulative_rewards is not None, "cumulative_rewards is not defined"

    return cumulative_rewards

def get_loss(logits, actions, rewards, n_actions=n_actions, gamma=0.99, entropy_coef=1e-2):
    """
    Compute the loss for the REINFORCE algorithm.
    """
    actions = torch.tensor(actions, dtype=torch.int32)
    cumulative_returns = np.array(get_cumulative_rewards(rewards, gamma))
    cumulative_returns = torch.tensor(cumulative_returns, dtype=torch.float32)
    # cumulative_returns = (cumulative_returns - cumulative_returns.mean()) / (cumulative_returns.std() + 1e-9)
    probs = nn.functional.softmax(logits, dim=-1)    
    log_probs = torch.log(probs)
    log_probs_for_actions = log_probs[range(log_probs.shape[0]), actions]
    J_hat = 1/log_probs_for_actions.shape[0] * torch.sum(log_probs_for_actions * cumulative_returns)
    
    entropy = -torch.sum(probs * log_probs, dim=1).mean()
    loss = -J_hat - entropy_coef * entropy

    return loss