


from stable_baselines.common.policies import MlpPolicy
from stable_baselines.common.policies import FeedForwardPolicy
from stable_baselines import PPO1
from simple_arg_parse import arg_or_default
import PCC_RL_train

import tensorflow as tf

import gym
arch_str = arg_or_default("--arch", default="30,16")
if arch_str == "":
    arch = []
else:
    arch = [int(layer_width) for layer_width in arch_str.split(",")]
print("Architecture is: %s" % str(arch))

training_sess = None

class MyMlpPolicy(FeedForwardPolicy):

    def __init__(self, sess, ob_space, ac_space, n_env, n_steps, n_batch, reuse=False, **_kwargs):
        super(MyMlpPolicy, self).__init__(sess, ob_space, ac_space, n_env, n_steps, n_batch, reuse, net_arch=[{"pi":arch, "vf":arch}],
                                        feature_extraction="mlp", **_kwargs)
        global training_sess
        training_sess = sess
env = gym.make('PccRL-v0')
#env = gym.make('CartPole-v0')

gamma = arg_or_default("--gamma", default=0.99)
print("gamma = %f" % gamma)
model = PPO1(MyMlpPolicy, env, verbose=1, schedule='constant', timesteps_per_actorbatch=2048, optim_batchsize=512, gamma=gamma,tensorboard_log="PPO_tensorboard/")

for i in range(0, 3):
    with model.graph.as_default():                                                                   
        saver = tf.train.Saver()                                                                     
        saver.save(training_sess, "./pcc_model_%d.ckpt" % i)
    print(i)
    model.learn(total_timesteps=4096,tb_log_name="%d_run" % i, reset_num_timesteps=False)


default_export_dir = "tmp/pcc_saved_models/model_C/"
export_dir = arg_or_default("--model-dir", default=default_export_dir)
with model.graph.as_default():

    pol = model.policy_pi#act_model

    obs_ph = pol.obs_ph
    act = pol.deterministic_action
    sampled_act = pol.action

    obs_input = tf.saved_model.utils.build_tensor_info(obs_ph)
    outputs_tensor_info = tf.saved_model.utils.build_tensor_info(act)
    stochastic_act_tensor_info = tf.saved_model.utils.build_tensor_info(sampled_act)
    signature = tf.saved_model.signature_def_utils.build_signature_def(
        inputs={"ob":obs_input},
        outputs={"act":outputs_tensor_info, "stochastic_act":stochastic_act_tensor_info},
        method_name=tf.saved_model.signature_constants.PREDICT_METHOD_NAME)

    #"""
    signature_map = {tf.saved_model.signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY:
                     signature}

    model_builder = tf.saved_model.builder.SavedModelBuilder(export_dir)
    model_builder.add_meta_graph_and_variables(model.sess,
        tags=[tf.saved_model.tag_constants.SERVING],
        signature_def_map=signature_map,
        clear_devices=True)
    model_builder.save(as_text=True)
