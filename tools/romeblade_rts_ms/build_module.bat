@echo off
set PYTHON=C:\Python27\python.exe
"%PYTHON%" process_init.py
"%PYTHON%" process_global_variables.py
"%PYTHON%" process_strings.py
"%PYTHON%" process_skills.py
"%PYTHON%" process_music.py
"%PYTHON%" process_animations.py
"%PYTHON%" process_meshes.py
"%PYTHON%" process_sounds.py
"%PYTHON%" process_skins.py
"%PYTHON%" process_map_icons.py
"%PYTHON%" process_factions.py
"%PYTHON%" process_items.py
"%PYTHON%" process_scenes.py
"%PYTHON%" process_troops.py
"%PYTHON%" process_particle_sys.py
"%PYTHON%" process_scene_props.py
"%PYTHON%" process_tableau_materials.py
"%PYTHON%" process_presentations.py
"%PYTHON%" process_party_tmps.py
"%PYTHON%" process_parties.py
"%PYTHON%" process_quests.py
"%PYTHON%" process_scripts.py
"%PYTHON%" process_mission_tmps.py
"%PYTHON%" process_game_menus.py
"%PYTHON%" process_simple_triggers.py
"%PYTHON%" process_dialogs.py
"%PYTHON%" process_global_variables_unused.py
del /Q *.pyc 2>nul
echo Script processing has ended.
exit /b 0
