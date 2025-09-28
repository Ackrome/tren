# coding: utf-8

import numpy as np

n_states = 500 # for Taxi-v3
n_actions = 6 # for Taxi-v3

def select_elites(states_batch, actions_batch, rewards_batch, percentile=50):
    """
    Select states and actions from games that have rewards >= percentile
    :param states_batch: list of lists of states, states_batch[session_i][t]
    :param actions_batch: list of lists of actions, actions_batch[session_i][t]
    :param rewards_batch: list of rewards, rewards_batch[session_i]

    :returns: elite_states,elite_actions, both 1D lists of states and respective actions from elite sessions

    Please return elite states and actions in their original order
    [i.e. sorted by session number and timestep within session]

    If you are confused, see examples below. Please don't assume that states are integers
    (they will become different later).
    """
    indices = np.where(rewards_batch >= np.percentile(rewards_batch,percentile))[0]
    elite_states,elite_actions =[],[]
    for idx in indices:
        elite_states.extend(states_batch[idx])
        elite_actions.extend(actions_batch[idx])
    
    return elite_states, elite_actions

def update_policy(elite_states, elite_actions, n_states=n_states, n_actions=n_actions):
    """
    Given old policy and a list of elite states/actions from select_elites,
    return new updated policy where each action probability is proportional to

    policy[s_i,a_i] ~ #[occurences of si and ai in elite states/actions]

    Don't forget to normalize policy to get valid probabilities and handle 0/0 case.
    In case you never visited a state, set probabilities for all actions to 1./n_actions

    :param elite_states: 1D list of states from elite sessions
    :param elite_actions: 1D list of actions from elite sessions

    """
    new_policy = np.zeros((n_states, n_actions))
    for i, j in zip(elite_states, elite_actions):
        new_policy[i,j] +=1
    
    for i in range(n_states):
        if new_policy[i].sum()==0:
            new_policy[i] = np.ones(n_actions)
    
    new_policy = new_policy/np.sum(new_policy,axis=1, keepdims=True)
    return new_policy

def generate_session(env, policy, t_max=int(10**4)):
    """
    Play game until end or for t_max ticks.
    :param policy: an array of shape [n_states,n_actions] with action probabilities
    :returns: list of states, list of actions and sum of rewards
    """
    states, actions = [], []
    total_reward = 0.

    s, info = env.reset()

    for t in range(t_max):
        a = np.random.choice(len(policy[s]),p=policy[s])
        new_s, r, done, truncated, info = env.step(a)
        assert new_s is not None and r is not None and done is not None
        assert a is not None
        states.append(s)
        actions.append(a)
        total_reward += r

        s = new_s
        if done:
            break
    return states, actions, total_reward