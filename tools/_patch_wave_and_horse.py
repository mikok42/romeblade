# -*- coding: ascii -*-
from __future__ import print_function
import io
import os

ROOT = r"c:\Users\Mikok\Documents\RomeAndBlade\tools\romeblade_rts_ms"


def read(p):
    with io.open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write_ascii(p, text, nl="\r\n"):
    text = "".join(ch if ord(ch) < 128 else "?" for ch in text)
    # normalize to file newline style
    text = text.replace("\r\n", "\n").replace("\n", nl)
    with io.open(p, "w", encoding="ascii", newline="") as f:
        f.write(text)
    print("wrote", p, "len", len(text))


def main():
    # ---- constants ----
    p = os.path.join(ROOT, "module_constants.py")
    t = read(p)
    nl = "\r\n" if "\r\n" in t else "\n"
    marker = "########################################################" + nl + "##  ITEM SLOTS"
    block = (
        nl
        + "########################################################"
        + nl
        + "##  ROMEBLADE WAVE BATTLE (easy knobs)"
        + nl
        + "########################################################"
        + nl
        + "# Total army sizes entering the fight (reserves + first wave)."
        + nl
        + "rb_wave_army_a = 300          # player side"
        + nl
        + "rb_wave_army_b = 150          # enemy side"
        + nl
        + "# Max humans on the field at once (both sides combined, not counting the player hero)."
        + nl
        + "rb_wave_field_cap = 90"
        + nl
        + "# When a side's living troops fall below this percent of its field target, refill from reserve."
        + nl
        + "rb_wave_refill_pct = 50"
        + nl
        + "# Max new agents spawned for one side in a single refill pulse (keeps hitch small)."
        + nl
        + "rb_wave_spawn_chunk = 12"
        + nl
        + "# Seconds between wave checks."
        + nl
        + "rb_wave_check_interval = 3"
        + nl
        + nl
    )
    if "rb_wave_army_a" not in t:
        if marker not in t:
            raise SystemExit("constants marker missing repr=%r" % (t[200:350],))
        t = t.replace(marker, block + marker, 1)
        write_ascii(p, t, nl)
    else:
        print("constants already present")

    # ---- strings ----
    p = os.path.join(ROOT, "module_strings.py")
    t = read(p)
    if "romeblade_wave_hud" not in t:
        old = '("romeblade_rts_order_follow","Order: FOLLOW."),'
        add = '''("romeblade_rts_order_follow","Order: FOLLOW."),
  ("romeblade_wave_title","RomeBlade Wave Battle: your host vs the foe. Troops arrive in waves matching the entry ratio until reserves run out."),
  ("romeblade_wave_hud","CONTROLS^F10 bird-eye | WASD move | Q down E up | Shift faster^F9 hold-at-point | F8 charge | F7 follow | Backspace orders^WAVE  field-cap {reg5}  refill@{reg6}%^YOU on-field:{reg3} reserve:{reg1}  |  ENEMY on-field:{reg4} reserve:{reg2}"),
  ("romeblade_wave_win","Wave battle won - the enemy host is spent."),
  ("romeblade_wave_lose","Wave battle lost - your host is spent."),'''
        if old not in t:
            raise SystemExit("string anchor missing")
        t = t.replace(old, add, 1)
        write_ascii(p, t, "\r\n" if "\r\n" in t else "\n")
    else:
        print("strings already present")

    # ---- horse freeze in camera ----
    p = os.path.join(ROOT, "module_mission_templates.py")
    t = read(p)
    nl = "\r\n" if "\r\n" in t else "\n"

    old_toggle_on = """      (position_get_x, \"$g_rts_stash_x\", pos53),
      (position_get_y, \"$g_rts_stash_y\", pos53),
      (agent_set_position, \":player_agent\", pos53),
      (assign, \"$g_rts_body_stashed\", 1),
      (agent_set_hit_points, \":player_agent\", 100, 0),"""

    new_toggle_on = """      (position_get_x, \"$g_rts_stash_x\", pos53),
      (position_get_y, \"$g_rts_stash_y\", pos53),
      (agent_get_horse, \":horse_agent\", \":player_agent\"),
      (try_begin),
        (ge, \":horse_agent\", 0),
        (agent_set_position, \":horse_agent\", pos53),
        (agent_set_hit_points, \":horse_agent\", 100, 0),
        (agent_set_scripted_destination, \":horse_agent\", pos53, 1),
      (try_end),
      (agent_set_position, \":player_agent\", pos53),
      (agent_set_scripted_destination, \":player_agent\", pos53, 1),
      (assign, \"$g_rts_body_stashed\", 1),
      (agent_set_hit_points, \":player_agent\", 100, 0),"""

    # fix escaping - the file uses normal quotes
    old_toggle_on = old_toggle_on.replace('\\"', '"')
    new_toggle_on = new_toggle_on.replace('\\"', '"')

    if "Freeze rider AND horse" not in t and "agent_get_horse, \":horse_agent\"" not in t.replace('"', '"'):
        pass

    if "(agent_get_horse, \":horse_agent\", \":player_agent\")," not in t and '(agent_get_horse, ":horse_agent", ":player_agent"),' not in t:
        if old_toggle_on not in t:
            raise SystemExit("toggle_on anchor missing")
        t = t.replace(old_toggle_on, new_toggle_on, 1)
        print("patched toggle horse")
    else:
        print("toggle horse already patched")

    old_toggle_off = """      (position_set_z_to_ground_level, pos54),
      (position_move_z, pos54, 30),
      (agent_set_position, ":player_agent", pos54),
      (assign, "$g_rts_body_stashed", 0),"""

    new_toggle_off = """      (position_set_z_to_ground_level, pos54),
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

    if "(agent_clear_scripted_mode, \":player_agent\")," not in t and '(agent_clear_scripted_mode, ":player_agent"),' not in t:
        if old_toggle_off not in t:
            raise SystemExit("toggle_off anchor missing")
        t = t.replace(old_toggle_off, new_toggle_off, 1)
        print("patched toggle off horse")
    else:
        print("toggle off already patched")

    old_tick_freeze = """    # Freeze body so WASD/stock move bindings cannot walk the soldier.
    (init_position, pos55),
    (position_set_x, pos55, "$g_rts_stash_x"),
    (position_set_y, pos55, "$g_rts_stash_y"),
    (position_set_z, pos55, 5000),
    (agent_set_position, ":player_agent", pos55),
    (agent_set_hit_points, ":player_agent", 100, 0),"""

    new_tick_freeze = """    # Freeze rider AND horse so mounted WASD cannot roam while camera is up.
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

    if "Freeze rider AND horse" not in t:
        if old_tick_freeze not in t:
            raise SystemExit("tick freeze anchor missing")
        t = t.replace(old_tick_freeze, new_tick_freeze, 1)
        print("patched tick horse")
    else:
        print("tick horse already patched")

    write_ascii(p, t, nl)

    # ---- scripts for wave ----
    p = os.path.join(ROOT, "module_scripts.py")
    t = read(p)
    if '("romeblade_wave_count_side"' not in t and '("romeblade_wave_count_side"' not in t:
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
      # param1 = team (0/1), param2 = how many to spawn
      (store_script_param_1, ":team_no"),
      (store_script_param_2, ":num"),
      (try_begin),
        (gt, ":num", 0),
        (try_begin),
          (eq, ":team_no", 0),
          (assign, ":entry", 2),
          (assign, ":troop", "trp_swadian_infantry"),
        (else_try),
          (assign, ":entry", 17),
          (assign, ":troop", "trp_vaegir_infantry"),
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
          (agent_set_slot, ":new_agent", slot_agent_is_not_reinforcement, 0),
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
        (assign, ":alive", 0),
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
        # insert before final closing of scripts list - before last `]`
        # Find custom_battle_end script end and insert after
        anchor = '  # script_remove_troop_from_prison'
        if anchor not in t:
            raise SystemExit("scripts anchor missing")
        t = t.replace(anchor, insert + "\n  # script_remove_troop_from_prison", 1)
        write_ascii(p, t, nl)
        print("added wave scripts")
    else:
        print("wave scripts already present")

    # ---- mission template ----
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

      # Wave refill + HUD
      (rb_wave_check_interval, 0, 0, [],
        [
          (call_script, "script_romeblade_wave_refill_side", 0),
          (call_script, "script_romeblade_wave_refill_side", 1),
          (call_script, "script_romeblade_wave_update_hud"),
         ]),

      # Victory: enemy field empty and enemy reserve empty
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

      # Defeat: our field empty (besides fallen player handling) and our reserve empty,
      # or player fallen with no allies left and no reserve.
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
        if not t.rstrip().endswith("]"):
            raise SystemExit("mission_templates end marker weird")
        # insert before final ]
        idx = t.rfind("\n]")
        if idx < 0:
            raise SystemExit("cannot find end of mission_templates")
        t = t[:idx] + mt + t[idx:]
        write_ascii(p, t, nl)
        print("added wave mission template")
    else:
        print("wave mission already present")

    # ---- menu entry ----
    p = os.path.join(ROOT, "module_game_menus.py")
    t = read(p)
    if "romeblade_wave_battle_entry" not in t:
        menu_item = r'''
      ("romeblade_wave_battle_entry",[],"RomeBlade Wave Battle (300 vs 150)",
       [
           # Easy knobs live in module_constants.py (rb_wave_*).
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

           # First wave only (field targets), split across entries.
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
        anchor = '("custom_battle_scenario_1",[], "Skirmish 1",'
        # find the option list after start_game_3 - insert as first option
        needle = '    [\n      ("custom_battle_scenario_1",[], "Skirmish 1",'
        if needle not in t:
            needle = '    [\r\n      ("custom_battle_scenario_1",[], "Skirmish 1",'
        if needle not in t:
            # try simpler
            idx = t.find('("custom_battle_scenario_1",[], "Skirmish 1",')
            if idx < 0:
                raise SystemExit("menu skirmish anchor missing")
            # insert before this option
            t = t[:idx] + menu_item.strip() + "\n      " + t[idx:]
        else:
            t = t.replace(needle, "    [\n" + menu_item + '      ("custom_battle_scenario_1",[], "Skirmish 1",', 1)
        write_ascii(p, t, nl)
        print("added menu entry")
    else:
        print("menu entry already present")

    print("ALL PATCHES DONE")


if __name__ == "__main__":
    main()
