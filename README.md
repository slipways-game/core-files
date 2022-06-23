# core-files

This is an extract from Slipways **core scripts**. Everything that you can find in the core game: the technologies, races, perks, campaign missions, etc. is derived from these files. If you want to do something, chances are you can find something in the core game that does something similar, and adapt the spreadsheets/code from the core files. The idea is for these files to serve as one giant example of how to do anything possible in Slipways with scripts.

The main file you should look at is `game.xls`, which describes most of the scriptable objects in the game. From there, you will see references to code stored in `.py` files which describes the gameplay logic backing those objects. The best strategy is usually to search through these files (using your editor's "Find in all files..." functionality or something like `grep`) for refrences to the thing you'd like to learn more about.

The campaign mission files also contain a lot of interesting examples. You can find their `.xls` and `.py` files in `modes\campaign-diaspora\m-<mission-id>`. The custom sector types are also defined there.

For more limited, but more curated examples, we also have [example mods available](https://github.com/slipways-game/example-mods).
