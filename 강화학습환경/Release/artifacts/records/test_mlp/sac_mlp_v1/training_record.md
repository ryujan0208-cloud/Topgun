# Training Record

- Created at: `2026-06-22T19:39:25`
- Python: `3.11.15`
- Platform: `Windows-10-10.0.26200-SP0`
- Algorithm: `sac`

## Observation

- Mode: `tactical16`
- Size: `16`
- Description: Full tactical observation: ownship attitude + speed + altitude + health, relative geometry (ATA, AA, LOS), target health, WEZ flag, pursuit score. All features normalized to [-1, 1]. Observation space bounds: [-1, 1].
- Features:
  - `ownship_roll_norm`
  - `ownship_pitch_norm`
  - `ownship_yaw_norm`
  - `ownship_speed_norm`
  - `ownship_alt_norm`
  - `ownship_health_norm`
  - `delta_n_norm`
  - `delta_e_norm`
  - `delta_d_norm`
  - `ata_norm`
  - `aa_norm`
  - `az_norm`
  - `el_norm`
  - `target_health_norm`
  - `in_wez`
  - `pursuit_score_norm`

## Reward

- Description: Survival bonus (curriculum) + step penalty + pursuit shaping (smooth ATA×range gradient) + damage differential + low altitude penalty + terminal rewards.
- Step penalty: `-0.01`
- Damage scale: `20.0`
- Pursuit scale: `0.3`
- Pursuit half angle (deg): `30.0`
- Pursuit range (m): `3000.0`
- Low altitude penalty: `0.1`
- Win reward: `100.0`
- Loss reward: `-100.0`
- Draw reward: `-30.0`

## CLI Arguments

```json
{
  "algorithm": "sac",
  "iterations": 50,
  "framework": "torch",
  "num_env_runners": 1,
  "num_envs_per_env_runner": 1,
  "rollout_fragment_length": "auto",
  "batch_mode": "truncate_episodes",
  "observation_mode": "tactical16",
  "observation_module": "",
  "target_mode": "behavior_tree",
  "target_behavior_dll": "AIP_BASE_target.dll",
  "reward_module": "",
  "max_engage_time": 60.0,
  "episode_step_limit": 3600,
  "lr": 0.0003,
  "gamma": 0.99,
  "train_batch_size": 256,
  "minibatch_size": 256,
  "gae_lambda": 0.95,
  "clip_param": 0.2,
  "tau": 0.005,
  "target_entropy": "auto",
  "replay_buffer_capacity": 10000,
  "model_fcnet_hiddens": "256,256",
  "model_fcnet_activation": "relu",
  "model_head_fcnet_hiddens": "",
  "model_head_fcnet_activation": "relu",
  "model_vf_share_layers": null,
  "network_spec_json": "",
  "use_lstm": false,
  "use_lstm_sac": false,
  "lstm_scope": "actor_only",
  "lstm_cell_size": 64,
  "max_seq_len": 8,
  "debug_io": false,
  "use_lstm_prioritized_replay": false,
  "output_name": "test_mlp",
  "output_tag": "sac_mlp_v1",
  "notes": "Student SAC MLP baseline. Edit env/algo/runtime/log sections for experiments.",
  "save_lightweight_bundle": true,
  "lightweight_bundle_frequency": 5,
  "save_native_checkpoint": true,
  "restore_checkpoint": "",
  "init_bundle": "",
  "use_tune": false,
  "checkpoint_frequency": 0,
  "native_checkpoint_frequency": 25,
  "dashboard_logdir": "artifacts/dashboard",
  "disable_dashboard_log": false,
  "policy_probe_interval": 10,
  "policy_probe_steps": 4,
  "no_policy_probe_print": false,
  "engagement_log_interval": 0,
  "engagement_log_steps": 600,
  "engagement_log_episodes": 1,
  "no_engagement_log_print": false,
  "experiment_yaml": "C:\\Users\\TFX5470H\\Desktop\\.topgun\\강화학습환경\\Release\\experiments\\student_sac_mlp.yaml"
}
```

## Environment Config

```json
{
  "observation_mode": "tactical16",
  "target_mode": "behavior_tree",
  "target_behavior_dll": "AIP_BASE_target.dll",
  "ownship_control_mode": "rl",
  "max_engage_time": 60.0,
  "episode_step_limit": 3600,
  "step_ratio": 6,
  "wez": {
    "angle_deg": 2.0,
    "min_range_m": 152.4,
    "max_range_m": 914.4
  },
  "target_loiter": {
    "enabled": true,
    "bank": 30.0,
    "pitch": 0.0
  },
  "target_autopilot": {
    "heading_cmd": 180.0,
    "altitude_cmd": 7000.0,
    "speed_cmd": 250.0
  },
  "reward": {
    "step_penalty": -0.01,
    "damage_scale": 20.0,
    "pursuit_scale": 0.3,
    "pursuit_half_angle_deg": 30.0,
    "pursuit_range_m": 3000.0,
    "low_altitude_penalty": 0.1,
    "win_reward": 100.0,
    "loss_reward": -100.0,
    "draw_reward": -30.0,
    "guard_fail_penalty": -50.0,
    "mode": "default"
  }
}
```

## Training History

- iter `0`: reward_mean=`n/a`, episode_len_mean=`n/a`
- iter `1`: reward_mean=`n/a`, episode_len_mean=`n/a`
- iter `2`: reward_mean=`n/a`, episode_len_mean=`n/a`
- iter `3`: reward_mean=`-31.092087828848655`, episode_len_mean=`381.0`
- iter `4`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `5`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `6`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `7`: reward_mean=`-29.98434259848771`, episode_len_mean=`395.0`
- iter `8`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `9`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `10`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `11`: reward_mean=`-31.18642930488601`, episode_len_mean=`346.0`
- iter `12`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `13`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `14`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `15`: reward_mean=`-30.21368324943833`, episode_len_mean=`403.0`
- iter `16`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `17`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `18`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `19`: reward_mean=`-30.5541790742252`, episode_len_mean=`413.0`
- iter `20`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `21`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `22`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `23`: reward_mean=`-31.41152561960432`, episode_len_mean=`380.0`
- iter `24`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `25`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `26`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `27`: reward_mean=`-32.503890610917765`, episode_len_mean=`425.0`
- iter `28`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `29`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `30`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `31`: reward_mean=`-31.324826137392364`, episode_len_mean=`378.0`
- iter `32`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `33`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `34`: reward_mean=`-31.347911688864716`, episode_len_mean=`353.0`
- iter `35`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `36`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `37`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `38`: reward_mean=`-33.454363480903965`, episode_len_mean=`348.0`
- iter `39`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `40`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `41`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `42`: reward_mean=`-32.05584950099472`, episode_len_mean=`410.0`
- iter `43`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `44`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `45`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `46`: reward_mean=`-30.661368171344918`, episode_len_mean=`440.0`
- iter `47`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `48`: reward_mean=`nan`, episode_len_mean=`nan`
- iter `49`: reward_mean=`nan`, episode_len_mean=`nan`
