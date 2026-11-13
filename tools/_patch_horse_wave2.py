# -*- coding: ascii -*-
from __future__ import print_function
import io
import os

ROOT = r"c:\Users\Mikok\Documents\RomeAndBlade\tools\romeblade_rts_ms"


def read(p):
    with io.open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p, text):
    nl = "\r\n" if "\r\n" in text else "\n"
    text = "".join(ch if ord(ch) < 128 else "?" for ch in text)
    text = text.replace("\r\n", "\n").replace("\n", nl)
    with io.open(p, "w", encoding="ascii", newline="") as f:
        f.write(text)


def main():
    p = os.path.join(ROOT, "module_mission_templates.py")
    t = read(p)
    start = t.find("romeblade_rts_camera_toggle")
    end = t.find("romeblade_rts_camera_triggers")
    if start < 0 or end < 0:
        raise SystemExit("camera block missing")
    block = t[start:end]
    if "Freeze rider AND horse" in block:
        print("horse already fixed in camera block")
    else:
        old_on = """      (position_get_x, "$g_rts_stash_x", pos53),
      (position_get_y, "$g_rts_stash_y", pos53),
      (agent_set_position, ":player_agent", pos53),
      (assign, "$g_rts_body_stashed", 1),
      (agent_set_hit_points, ":player_agent", 100, 0),"""
        new_on = """      (position_get_x, "$g_rts_stash_x", pos53),
      (position_get_y, "$g_rts_stash_y", pos53),
      (agent_get_horse, ":horse_agent", ":player_agent"),
      (try_begin),
        (ge, ":horse_agent", 0),
        (agent_set_position, ":horse_agent", pos53),
        (agent_set_hit_points, ":horse_agent", 100, 0),
        (agent_set_scripted_destination, ":horse_agent", pos53, 1),
      (try_end),
      (agent_set_position, ":player_agent", pos53),
      (agent_set_scripted_destination, ":player_agent", pos53, 1),
      (assign, "$g_rts_body_stashed", 1),
      (agent_set_hit_points, ":player_agent", 100, 0),"""
        old_off = """      (position_set_z_to_ground_level, pos54),
      (position_move_z, pos54, 30),
      (agent_set_position, ":player_agent", pos54),
      (assign, "$g_rts_body_stashed", 0),"""
        new_off = """      (position_set_z_to_ground_level, pos54),
      (position_move_z, pos54, 30),
      (agent_get_horse, ":horse_agent", ":player_agent"),
      (try_begin),
        (ge, ":horse_agent", 0),
        (agent_clear_scripted_mode, ":horse_agent"),
        (agent_set_position, ":horse_agent", pos54),
      (try_end),
      (agent_clear_scripted_mode, ":player_agent"),
      (agent_set_position, ":player_agent", pos54),
      (assign, "$g_rts_body_stashed", 0),"""
        old_tick = """    # Freeze body so WASD/stock move bindings cannot walk the soldier.
    (init_position, pos55),
    (position_set_x, pos55, "$g_rts_stash_x"),
    (position_set_y, pos55, "$g_rts_stash_y"),
    (position_set_z, pos55, 5000),
    (agent_set_position, ":player_agent", pos55),
    (agent_set_hit_points, ":player_agent", 100, 0),"""
        new_tick = """    # Freeze rider AND horse so mounted WASD cannot roam while camera is up.
    (init_position, pos55),
    (position_set_x, pos55, "$g_rts_stash_x"),
    (position_set_y, pos55, "$g_rts_stash_y"),
    (position_set_z, pos55, 5000),
    (agent_get_horse, ":horse_agent", ":player_agent"),
    (try_begin),
      (ge, ":horse_agent", 0),
      (agent_set_position, ":horse_agent", pos55),
      (agent_set_hit_points, ":horse_agent", 100, 0),
      (agent_set_scripted_destination, ":horse_agent", pos55, 1),
    (try_end),
    (agent_set_position, ":player_agent", pos55),
    (agent_set_scripted_destination, ":player_agent", pos55, 1),
    (agent_set_hit_points, ":player_agent", 100, 0),"""
        for name, old, new in (
            ("on", old_on, new_on),
            ("off", old_off, new_off),
            ("tick", old_tick, new_tick),
        ):
            # normalize newlines in needles to file style
            old_n = old.replace("\n", "\r\n") if "\r\n" in block else old
            new_n = new.replace("\n", "\r\n") if "\r\n" in block else new
            if old_n not in block:
                # try lf
                old_n = old.replace("\r\n", "\n")
                new_n = new.replace("\r\n", "\n")
            if old_n not in block:
                raise SystemExit("%s needle missing" % name)
            block = block.replace(old_n, new_n, 1)
            print("patched", name)
        t = t[:start] + block + t[end:]
        write(p, t)
        print("camera horse freeze written")

    # scripts
    p = os.path.join(ROOT, "module_scripts.py")
    t = read(p)
    if "romeblade_wave_count_side" not in t:
        insert = r'''
  ("romeblade_wave_count_side",
    [
      (store_script_param_1, ":team_no"),
      (assign, reg0, 0),
      (get_player_agent_no, ":player_agent"),
      (try_for_agents, ":agent_no"),
        (agent_is_human, ":agent_no"),
        (agent_is_alive, ":agent_no"),
        (neq, ":agent_no", ":player_agent"),
        (agent_get_team, ":agent_team", ":agent_no"),
        (eq, ":agent_team", ":team_no"),
        (val_add, reg0, 1),
      (try_end),
    ]),

  ("romeblade_wave_spawn_side",
    [
      (store_script_param_1, ":team_no"),
      (store_script_param_2, ":num"),
      (try_begin),
        (gt, ":num", 0),
        (try_begin),
          (eq, ":team_no", 0),
          (assign, ":entry", 2),
        (else_try),
          (assign, ":entry", 17),
        (try_end),
        (entry_point_get_position, pos40, ":entry"),
        (set_spawn_position, pos40),
        (try_for_range, ":i", 0, ":num"),
          (store_random_in_range, ":roll", 0, 3),
          (try_begin),
            (eq, ":team_no", 0),
            (try_begin),
              (eq, ":roll", 0),
              (assign, ":troop", "trp_swadian_infantry"),
            (else_try),
              (eq, ":roll", 1),
              (assign, ":troop", "trp_swadian_crossbowman"),
            (else_try),
              (assign, ":troop", "trp_swadian_man_at_arms"),
            (try_end),
          (else_try),
            (try_begin),
              (eq, ":roll", 0),
              (assign, ":troop", "trp_vaegir_infantry"),
            (else_try),
              (eq, ":roll", 1),
              (assign, ":troop", "trp_vaegir_archer"),
            (else_try),
              (assign, ":troop", "trp_vaegir_horseman"),
            (try_end),
          (try_end),
          (spawn_agent, ":troop"),
          (assign, ":new_agent", reg0),
          (agent_set_team, ":new_agent", ":team_no"),
        (try_end),
        (team_give_order, ":team_no", grc_everyone, mordr_charge),
      (try_end),
    ]),

  ("romeblade_wave_update_hud",
    [
      (call_script, "script_romeblade_wave_count_side", 0),
      (assign, reg3, reg0),
      (call_script, "script_romeblade_wave_count_side", 1),
      (assign, reg4, reg0),
      (assign, reg1, "$g_rb_reserve_a"),
      (assign, reg2, "$g_rb_reserve_b"),
      (assign, reg5, "$g_rb_field_cap"),
      (assign, reg6, "$g_rb_refill_pct"),
      (tutorial_message, "str_romeblade_wave_hud"),
    ]),

  ("romeblade_wave_refill_side",
    [
      (store_script_param_1, ":team_no"),
      (try_begin),
        (eq, ":team_no", 0),
        (call_script, "script_romeblade_wave_count_side", 0),
        (assign, ":alive", reg0),
        (assign, ":target", "$g_rb_target_a"),
        (assign, ":reserve", "$g_rb_reserve_a"),
      (else_try),
        (call_script, "script_romeblade_wave_count_side", 1),
        (assign, ":alive", reg0),
        (assign, ":target", "$g_rb_target_b"),
        (assign, ":reserve", "$g_rb_reserve_b"),
      (try_end),
      (store_mul, ":threshold", ":target", "$g_rb_refill_pct"),
      (val_div, ":threshold", 100),
      (try_begin),
        (gt, ":reserve", 0),
        (lt, ":alive", ":threshold"),
        (store_sub, ":need", ":target", ":alive"),
        (val_min, ":need", ":reserve"),
        (val_min, ":need", rb_wave_spawn_chunk),
        (gt, ":need", 0),
        (call_script, "script_romeblade_wave_spawn_side", ":team_no", ":need"),
        (try_begin),
          (eq, ":team_no", 0),
          (val_sub, "$g_rb_reserve_a", ":need"),
        (else_try),
          (val_sub, "$g_rb_reserve_b", ":need"),
        (try_end),
      (try_end),
    ]),

'''
        anchor = "  # script_remove_troop_from_prison"
        if anchor not in t:
            raise SystemExit("scripts anchor missing")
        t = t.replace(anchor, insert + "\n" + anchor, 1)
        write(p, t)
        print("wave scripts added")
    else:
        print("wave scripts already present")

    # mission template
    p = os.path.join(ROOT, "module_mission_templates.py")
    t = read(p)
    if '"romeblade_wave_battle"' not in t:
        mt = r'''
  (
    "romeblade_wave_battle",mtf_battle_mode,-1,
    "Your host meets the enemy in successive waves.",
    [
      (0,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (1,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (2,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (3,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (4,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (5,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (6,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (7,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (8,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (9,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (10,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (11,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (12,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (13,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (14,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (15,mtef_visitor_source|mtef_team_0,0,aif_start_alarmed,1,[]),
      (16,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (17,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (18,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (19,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (20,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (21,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (22,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (23,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (24,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (25,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (26,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (27,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (28,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (29,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (30,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
      (31,mtef_visitor_source|mtef_team_1,0,aif_start_alarmed,1,[]),
     ],
    [
      common_custom_battle_tab_press,
      common_custom_battle_question_answered,
      common_inventory_not_available,
      romeblade_rts_camera_init,
      romeblade_rts_camera_toggle,
      romeblade_rts_camera_tick,
      common_battle_order_panel,
      common_battle_order_panel_tick,

      (0, 0, ti_once, [],
        [
          (assign, "$g_battle_result", 0),
          (assign, "$battle_won", 0),
          (call_script, "script_combat_music_set_situation_with_culture"),
          (call_script, "script_romeblade_wave_update_hud"),
         ]),

      common_music_situation_update,

      (rb_wave_check_interval, 0, 0, [],
        [
          (call_script, "script_romeblade_wave_refill_side", 0),
          (call_script, "script_romeblade_wave_refill_side", 1),
          (call_script, "script_romeblade_wave_update_hud"),
         ]),

      (1, 5, ti_once,
        [
          (store_mission_timer_a, ":t"),
          (ge, ":t", 8),
          (call_script, "script_romeblade_wave_count_side", 1),
          (eq, reg0, 0),
          (eq, "$g_rb_reserve_b", 0),
          (neg|main_hero_fallen),
        ],
        [
          (assign, "$g_battle_result", 1),
          (assign, "$battle_won", 1),
          (display_message, "str_romeblade_wave_win"),
          (call_script, "script_custom_battle_end"),
          (finish_mission, 1),
        ]),

      (1, 5, ti_once,
        [
          (store_mission_timer_a, ":t"),
          (ge, ":t", 8),
          (call_script, "script_romeblade_wave_count_side", 0),
          (eq, reg0, 0),
          (eq, "$g_rb_reserve_a", 0),
        ],
        [
          (assign, "$g_battle_result", -1),
          (display_message, "str_romeblade_wave_lose"),
          (call_script, "script_custom_battle_end"),
          (finish_mission, 0),
        ]),

      (1, 4, ti_once,
        [
          (main_hero_fallen),
          (call_script, "script_romeblade_wave_count_side", 0),
          (eq, reg0, 0),
          (eq, "$g_rb_reserve_a", 0),
        ],
        [
          (assign, "$g_battle_result", -1),
          (display_message, "str_romeblade_wave_lose"),
          (call_script, "script_custom_battle_end"),
          (finish_mission, 0),
        ]),
    ],
  ),

'''
        idx = t.rfind("\n]")
        if idx < 0:
            idx = t.rfind("\r\n]")
        if idx < 0:
            raise SystemExit("end of mission_templates not found")
        t = t[:idx] + mt + t[idx:]
        write(p, t)
        print("wave mission added")
    else:
        print("wave mission already present")

    # menu
    p = os.path.join(ROOT, "module_game_menus.py")
    t = read(p)
    if "romeblade_wave_battle_entry" not in t:
        menu_item = '''("romeblade_wave_battle_entry",[],"RomeBlade Wave Battle (300 vs 150)",
       [
           (assign, "$g_rb_army_a", rb_wave_army_a),
           (assign, "$g_rb_army_b", rb_wave_army_b),
           (assign, "$g_rb_field_cap", rb_wave_field_cap),
           (assign, "$g_rb_refill_pct", rb_wave_refill_pct),
           (store_add, ":sum", "$g_rb_army_a", "$g_rb_army_b"),
           (store_mul, "$g_rb_target_a", "$g_rb_field_cap", "$g_rb_army_a"),
           (val_div, "$g_rb_target_a", ":sum"),
           (store_sub, "$g_rb_target_b", "$g_rb_field_cap", "$g_rb_target_a"),
           (val_max, "$g_rb_target_a", 1),
           (val_max, "$g_rb_target_b", 1),
           (store_sub, "$g_rb_reserve_a", "$g_rb_army_a", "$g_rb_target_a"),
           (store_sub, "$g_rb_reserve_b", "$g_rb_army_b", "$g_rb_target_b"),
           (val_max, "$g_rb_reserve_a", 0),
           (val_max, "$g_rb_reserve_b", 0),
           (assign, "$g_player_troop", "trp_knight_1_1"),
           (set_player_troop, "$g_player_troop"),
           (assign, "$g_custom_battle_scene", "scn_quick_battle_1"),
           (modify_visitors_at_site, "$g_custom_battle_scene"),
           (reset_visitors),
           (set_visitor, 0, "$g_player_troop"),
           (assign, ":left", "$g_rb_target_a"),
           (assign, ":chunk", ":left"),
           (val_div, ":chunk", 4),
           (val_max, ":chunk", 1),
           (set_visitors, 1, "trp_swadian_infantry", ":chunk"),
           (val_sub, ":left", ":chunk"),
           (set_visitors, 2, "trp_swadian_crossbowman", ":chunk"),
           (val_sub, ":left", ":chunk"),
           (set_visitors, 3, "trp_swadian_man_at_arms", ":chunk"),
           (val_sub, ":left", ":chunk"),
           (set_visitors, 4, "trp_swadian_infantry", ":left"),
           (assign, ":left", "$g_rb_target_b"),
           (assign, ":chunk", ":left"),
           (val_div, ":chunk", 3),
           (val_max, ":chunk", 1),
           (set_visitors, 16, "trp_vaegir_infantry", ":chunk"),
           (val_sub, ":left", ":chunk"),
           (set_visitors, 17, "trp_vaegir_archer", ":chunk"),
           (val_sub, ":left", ":chunk"),
           (set_visitors, 18, "trp_vaegir_horseman", ":left"),
           (str_store_string, s16, "str_romeblade_wave_title"),
           (set_jump_mission, "mt_romeblade_wave_battle"),
           (jump_to_menu, "mnu_custom_battle_end"),
           (jump_to_scene, "$g_custom_battle_scene"),
           (change_screen_mission),
        ]
       ),
      '''
        idx = t.find('("custom_battle_scenario_1",[], "Skirmish 1",')
        if idx < 0:
            raise SystemExit("menu anchor missing")
        t = t[:idx] + menu_item + t[idx:]
        write(p, t)
        print("menu entry added")
    else:
        print("menu already present")

    # ensure strings exist
    p = os.path.join(ROOT, "module_strings.py")
    t = read(p)
    if "romeblade_wave_hud" not in t:
        raise SystemExit("wave strings missing - rerun first patch strings")
    print("DONE")


if __name__ == "__main__":
    main()
