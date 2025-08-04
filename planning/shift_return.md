Thanks for clarifying. I’ll investigate whether Shift+Enter can be captured in a terminal environment using Prompt Toolkit, specifically considering compatibility with Warp and the integrated VSCode terminal. If it’s not feasible due to terminal limitations, I’ll confirm that and suggest best practice alternatives that work out of the box (like Option+Enter or Ctrl+J). I’ll report back with concrete findings and recommendations.


# Shift+Enter in Terminal and Prompt Toolkit

## Terminal Limitation of Shift+Enter

Yes – it is essentially **accurate that a standard terminal cannot detect** a **Shift+Enter** combination as distinct from a normal Enter key press. In a typical terminal environment, the **Enter/Return key** sends a carriage-return/newline character (e.g. `0x0D` or `0x0A`), and **adding the Shift modifier doesn’t alter the code sent**. There is “no practical way to distinguish” a Shift+Enter from an ordinary Enter in a vanilla terminal session. This is a well-known limitation – for example, IPython’s terminal interface explicitly notes that **Shift-Enter (and Ctrl-Enter) cannot be captured** in the terminal for this reason. Prompt\_toolkit (and any CLI library) is subject to the same limitation: if the underlying terminal emulator isn’t sending a different key code, prompt\_toolkit can’t bind a separate action to Shift+Enter.

In other words, **most terminal emulators do not emit a unique escape sequence for Shift+Enter by default**. The Shift key usually only modifies **printable characters** (like turning “a” into “A”), but **Enter is not a character that can be shifted**, so historically terminals treat Enter and Shift+Enter identically. That’s why your earlier attempt (`Key('s-enter')` in prompt\_toolkit) failed with an “invalid key” – prompt\_toolkit never receives a distinct `"s-enter"` signal at all. The research you saw was correct: this isn’t a prompt\_toolkit bug but a fundamental terminal I/O behavior.

## Extended Protocols Enabling Shift+Enter

The good news is that **modern terminal protocols have introduced extensions to overcome this limitation**. Many terminals now support an *“extended keyboard” mode* (often called **CSI-u mode** or the **`modifyOtherKeys`** feature) which **assigns unique escape sequences to keys with modifiers**, including Enter. In this mode, **Shift+Enter can send a distinct code** that an application can recognize. For example, under the CSI-u scheme, a plain Enter is `0x0d`, whereas **Shift+Enter would be sent as `CSI 13;2 u`** (and Ctrl+Enter as `CSI 13;5 u`).

This extended mode isn’t enabled by default, but many terminals **support it if the application requests it**. A Hacker News commenter points out that **“the best way to support keystrokes such as Ctrl-Enter and Shift-Enter in the terminal is CSI-u mode”**, and notes that it’s supported by most modern terminals now. In practice, this includes terminals like xterm (with `modifyOtherKeys`), iTerm2, Kitty, possibly Warp, Windows Terminal, and others that have adopted these enhanced key protocols. Kitty terminal in particular introduced a **“kitty keyboard protocol”** with similar goals – allowing apps to detect modified keys (including Shift+Enter) – but of course this works only when running in Kitty or another emulator that supports that protocol.

**Prompt Toolkit can technically handle these sequences** if they are sent – but you would need to **enable the mode and define the key bindings** manually. This usually means sending a specific escape sequence to tell the terminal to turn on **modifyOtherKeys/CSI-u mode**, and then customizing prompt\_toolkit’s input parser to map the incoming `CSI 13;2 u` sequence to a “Shift+Enter” event. (By default, prompt\_toolkit doesn’t enable or handle CSI-u sequences on its own – it assumes the default terminal behavior unless you extend it.)

**Important caveat:** While a lot of terminals *do* support these extensions, **“out-of-the-box” broad support is not guaranteed**. Older or simpler terminals might ignore the CSI-u mode request. Even among those that support it, the application has to know to activate it. There’s also a bit of complexity in implementing it (e.g. detecting at runtime if the terminal supports the feature, to avoid sending unknown sequences). In Reddit discussions, developers note that only a limited subset of emulators historically supported the Kitty/CSI-u protocols – though that subset is growing. In short, **it’s possible to capture Shift+Enter** by leveraging these modern protocols, **but it requires extra work and isn’t 100% universal**.

## Solutions and Workarounds

If your goal is a solution that **“works out of the box” across terminals**, the safest approach is to **use an alternate key combination** for inserting a newline in your prompt\_toolkit app (as you’ve been doing). In fact, many CLI programs use exactly such alternatives since Shift+Enter wasn’t available:

* **Use Ctrl+J** – This is a common choice for “newline without submit.” Ctrl+J sends the ASCII line-feed character (LF, `0x0A`), which terminals interpret as a newline (it’s essentially the same as pressing Enter in terms of character, but it can be bound separately in some apps). For example, Unix terminals historically treat **Ctrl+J as newline** because it’s the control-code for line feed. You can bind Ctrl+J in prompt\_toolkit to insert a `buffer.newline()` easily. This feels quite natural (many users won’t need to press Option) and works everywhere, since it doesn’t rely on any special terminal behavior.

* **Keep **Option/Alt + Enter**** – This is the solution you already implemented. Alt+Enter typically sends an escape-prefixed newline (essentially `ESC \n`), which prompt\_toolkit can interpret. It’s a bit less intuitive for users expecting Shift+Enter, but it’s a valid alternative. (Some terminal emulators or hosted consoles use Alt+Enter to mean “newline” as well – for instance, older Slack desktop apps used Option+Enter on macOS to insert a newline.)

* **Ctrl+O** – This is a somewhat lesser-known option, but IPython uses **Ctrl+O** in the terminal to insert blank lines without executing. In fact, IPython’s terminal mode added a feature where pressing Ctrl+O opens a new line *below* the current one (keeping indentation), specifically because Shift+Enter wasn’t available. You could consider a similar binding. (Ctrl+O sends the ASCII SI control code, which by itself doesn’t produce a visible character but can be caught by libraries like prompt\_toolkit.)

* **Esc then Enter** – As you noted, hitting Escape followed by Enter is a two-stroke solution but will reliably produce a newline in some contexts. (For example, in Vim’s insert mode, one often uses `Esc + o` to open a new line – somewhat analogous conceptually.) This is more of an emergency workaround than a user-friendly shortcut, so it’s typically not the first choice.

Given that **Shift+Enter is not natively distinguishable in terminals**, sticking with one (or multiple) of the above **workarounds is recommended** for broad compatibility. Among these, **Ctrl+J** is a popular and ergonomically simple choice – it behaves like the standard “newline” in many terminal-based editors or REPLs, so users might even try it instinctively. You could support **both** Option+Enter and Ctrl+J to insert newlines, to cover both Mac-centric and Unix-standard habits.

## Conclusion

In summary, your understanding was correct: **by default Shift+Enter cannot be captured in a typical terminal app** (the terminal doesn’t send a unique code for it). There *is* a technical path to make it work by enabling extended key reporting (CSI-u/modifyOtherKeys), which prompt\_toolkit could then handle – but that requires additional coding and is not guaranteed to work everywhere without configuration. If you need a reliable out-of-the-box solution, it’s better to **continue with an alternative key combo** for newline insertion.

Your current **Option/Alt+Return solution is valid**, and you can consider **adding Ctrl+J** as an intuitive cross-platform “newline” shortcut. This way, users in most terminals (Warp, VSCode’s built-in terminal, xterm, etc.) will be able to insert new lines easily, and those who try the typical Slack-style Shift+Enter will at least be informed (via documentation or an on-screen hint) to use the alternate shortcut.

Ultimately, unless you’re prepared to implement and **maintain the CSI-u workaround**, using the simpler key binding alternatives is the practical way to go. This ensures your prompt-toolkit application will **work consistently across all terminals** without special setup – avoiding reliance on a feature that, while possible, isn’t yet universal.

**Sources:**

* IPython 5.x documentation – cannot distinguish Shift-Enter in terminal
* Leonerd’s “Fix Terminals” spec – extended encoding for modified keys (Shift-Enter = CSI `13;2u`)
* Discussion on extended key protocols (CSI-u mode supported in modern terminals)
* Reddit discussion (limited default support for Shift+Enter, Kitty protocol as a solution)

Citations
5.x Series — IPython 8.21.0 documentation

https://ipython.readthedocs.io/en/8.21.0/whatsnew/version5.html

Shift+enter in terminal not possible, what's my alternative? : r/golang

https://www.reddit.com/r/golang/comments/1hdckee/shiftenter_in_terminal_not_possible_whats_my/
Fix Terminals - Please

http://www.leonerd.org.uk/hacks/fixterms/
Show HN: Euporie, a Tui for Jupyter Notebooks | Hacker News

https://news.ycombinator.com/item?id=27091167

Shift+enter in terminal not possible, what's my alternative? : r/golang

https://www.reddit.com/r/golang/comments/1hdckee/shiftenter_in_terminal_not_possible_whats_my/
5.x Series — IPython 8.21.0 documentation

https://ipython.readthedocs.io/en/8.21.0/whatsnew/version5.html