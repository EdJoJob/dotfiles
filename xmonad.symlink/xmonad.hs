-- vim: foldmethod=marker
-- IMPORTS {{{
    -- Base {{{
import XMonad
import System.IO (hPutStrLn)
import System.Exit (exitSuccess)
import Control.Monad (liftM2)
import Text.Printf (printf)
import qualified XMonad.StackSet as W
import qualified Data.Map as M
    -- }}}
    -- Actions {{{
import XMonad.Actions.CycleWS
    -- }}}
    -- Hooks {{{
import XMonad.Hooks.DynamicLog
import XMonad.Hooks.EwmhDesktops
import XMonad.Hooks.FadeInactive
import XMonad.Hooks.ManageDocks
import XMonad.Hooks.SetWMName
    -- }}}
    -- Layout modifiers {{{
import XMonad.Layout.NoBorders
import XMonad.Layout.PerWorkspace
import XMonad.Layout.Reflect
import XMonad.Layout.ToggleLayouts
    -- }}}
    -- Layouts {{{
import XMonad.Layout.IM
import XMonad.Layout.Mosaic
import XMonad.Layout.ResizableTile
    -- }}}

    --Utilities {{{
import XMonad.Util.EZConfig(additionalKeys)
import XMonad.Util.Run(spawnPipe)
    -- }}}
-- }}}

-- VARIABLES {{{

myBaseConfig = defaultConfig
myFont :: [Char]
myFont = "xft:mononoki-Regular Nerd Font Complete Mono:pixelsize=12"

myModMask :: KeyMask
myModMask = (mod4Mask) -- Sets mod to super

myTerminal :: [Char]
myTerminal = "gnome-terminal" -- Set default terminal

myBorderWidth :: Dimension
myBorderWidth = 2          -- Sets border width for windows

myWorkspaces = ["1:code", "2:web", "3:term", "4:mail", "5:gimp", "6:misc", "7:junk", "8:fullscreen", "9:im"]
myNormalBorderColor = "#dddddd"
myFocusedBorderColor = "#ffff00"
-- }}}

-- KEYS {{{
myKeys conf@(XConfig {XMonad.modMask = modMask}) = M.fromList $
  -- launching and killing programs
    [ ((modMask .|. shiftMask, xK_Return), spawn $ XMonad.terminal conf) -- %! Launch terminal
    , ((mod4Mask .|. shiftMask, xK_z), spawn "slock")

    , ((modMask,               xK_p     ), spawn $ printf "exe=`dmenu_path | dmenu -sf '#ffffff' -sb '#008800' -nb '#333333' -nf '#aaaaaa' -fn %s` && eval \"exec $exe\"" (show myFont)) -- %! Launch dmenu
    , ((modMask .|. shiftMask, xK_p     ), spawn "gmrun") -- %! Launch gmrun
    , ((modMask .|. shiftMask, xK_c     ), kill) -- %! Close the focused window

    , ((modMask,               xK_space ), sendMessage NextLayout) -- %! Rotate through the available layout algorithms
    , ((modMask .|. shiftMask, xK_space ), setLayout $ XMonad.layoutHook conf) -- %!  Reset the layouts on the current workspace to default

    , ((modMask,               xK_n     ), refresh) -- %! Resize viewed windows to the correct size

    -- move focus up or down the window stack
    , ((mod1Mask,               xK_Tab   ), windows W.focusDown) -- %! Move focus to the next window
    , ((mod1Mask .|. shiftMask, xK_Tab   ), windows W.focusUp  ) -- %! Move focus to the previous window

    , ((modMask,               xK_j     ), windows W.focusDown) -- %! Move focus to the next window
    , ((modMask,               xK_k     ), windows W.focusUp  ) -- %! Move focus to the previous window
    , ((modMask .|. shiftMask,               xK_m     ), windows W.focusMaster  ) -- %! Move focus to the master window

    -- modifying the window order
    , ((modMask,               xK_Return), windows W.swapMaster) -- %! Swap the focused window and the master window
    , ((modMask .|. shiftMask, xK_j     ), windows W.swapDown  ) -- %! Swap the focused window with the next window
    , ((modMask .|. shiftMask, xK_k     ), windows W.swapUp    ) -- %! Swap the focused window with the previous window

    -- resizing the master/slave ratio
    , ((modMask,               xK_h     ), sendMessage Shrink) -- %! Shrink the master area
    , ((modMask,               xK_l     ), sendMessage Expand) -- %! Expand the master area

    -- kill long running command announcement
    , (( mod1Mask .|. controlMask, xK_z ), spawn "killall espeak")

    -- floating layer support
    , ((modMask,               xK_t     ), withFocused $ windows . W.sink) -- %! Push window back into tiling

    -- increase or decrease number of windows in the master area
    , ((modMask              , xK_comma ), sendMessage (IncMasterN 1)) -- %! Increment the number of windows in the master area
    , ((modMask              , xK_period), sendMessage (IncMasterN (-1))) -- %! Deincrement the number of windows in the master area

    -- toggle the status bar gap
    , ((modMask              , xK_b     ), sendMessage $ ToggleStruts) -- %! Toggle the status bar gap

    -- quit, or restart
    , ((modMask .|. shiftMask, xK_q     ), io (exitSuccess)) -- %! Quit xmonad
    , ((modMask              , xK_q     ), spawn "xmonad --recompile && xmonad --restart") -- %! Restart xmonad


    -- Movements
    , (( controlMask .|. mod4Mask, xK_l ), nextWS)
    , (( controlMask .|. mod4Mask, xK_h), prevWS)
    , (( controlMask .|. mod4Mask .|. mod1Mask, xK_l), shiftToNext >> nextWS)
    , (( controlMask .|. mod4Mask .|. mod1Mask, xK_h), shiftToPrev >> prevWS)

    -- layout screens

    --1920 X 1080

    -- , ((modMask .|. shiftMask, xK_space), layoutScreens 3 $ fixedLayout [Rectangle 0 0 1920 (1080), Rectangle 1920 0 1224 1080, Rectangle (1920 + 1224) 0 (1920 - 1224) 1080])
    --, ((modMask .|. shiftMask, xK_space), layoutScreens 3 $ fixedLayout [Rectangle 0 0 1224 (1080), Rectangle 1224 0 (1920 - 1224) 1080, Rectangle 1920 0 1224 1080, Rectangle (1920 + 1224) 0 (1920 - 1224) 1080])
    --, ((modMask .|. shiftMask, xK_space), layoutScreens 3 $ fixedLayout [Rectangle 0 0 (screenWidth) (screenHeight), Rectangle screenWidth 0 midScreenWidth screenHeight, Rectangle (screenWidth + midScreenWidth) 0 (screenWidth - midScreenWidth) screenHeight])
    , ((modMask .|. controlMask .|. shiftMask, xK_space), rescreen)

    -- misc control
    , ((modMask, xK_x     ), spawn "nautilus") -- %! open nautilus

    ]
    ++
    -- mod-[1..9] %! Switch to workspace N
    -- mod-shift-[1..9] %! Move client to workspace N
    [((m .|. controlMask .|. mod4Mask, k), windows $ f i)
        | (i, k) <- zip (XMonad.workspaces conf) [xK_1 .. xK_9]
        , (f, m) <- [(W.greedyView, 0), (liftM2 (.) W.greedyView W.shift, mod1Mask)]]
    ++
    -- mod-{w,e,r} %! Switch to physical/Xinerama screens 1, 2, or 3
    -- mod-shift-{w,e,r} %! Move client to screen 1, 2, or 3
    [((m .|. controlMask .|. mod4Mask, key), screenWorkspace sc >>= flip whenJust (windows . f))
        | (key, sc) <- zip [xK_w, xK_e, xK_r] [0..]
        , (f, m) <- [(W.view, 0), (W.shift, mod1Mask)]]
-- }}}

-- workspaces{{{
myLayoutHook = onWorkspace "5:gimp" gimp $
    onWorkspace "3:term"  tiled $
        onWorkspace "9:im"  tiled $
            onWorkspace "8:fullscreen"  (noBorders Full) $
                avoidStruts $ toggleLayouts (noBorders Full)
    ( tiled ||| Full ||| mosaic 2 [3,2] ||| Mirror tiled)
        where
            tiled   = avoidStruts $ResizableTall nmaster delta ratio []
            nmaster = 1
            delta   = 2/100
            ratio   = 1/2
            gimp    =  withIM (0.11) (Role "gimp-toolbox") $
                        reflectHoriz $
                        withIM (0.15) (Role "gimp-dock") Full
--- }}}

-- manageHook {{{
myManageHook = composeAll
    [ className =? "Vncviewer"     --> doFloat
    , className =? "Thunderbird"   --> doF (W.shift "4:mail")
    , className =? "Slack"         --> doF (W.shift "9:im")
    ]
-- }}}

-- logHook {{{
myLogHook xmproc = do
    dynamicLogWithPP xmobarPP
                    { ppOutput = hPutStrLn xmproc
                    , ppTitle = xmobarColor "green" "" . shorten 50
                    }
    fadeInactiveLogHook 0.8
-- }}}

-- startupHook {{{
{- startup command for window effects

"-cfF" "c" is for soft shadows and transparency support,
       "f" for fade in & fade out when creating and closing windows,
       and "F" for fade when changing a window's transparency.
"-t-9 -l-11" shadows are offset 9 pixels from top of the window
             and 11 pixels from the left edge
"-r9" shadow radius is 9 pixels
"-o.95" shadow opacity is set to 0.95
"-D6" the time between each step when fading windows is set to 6 milliseconds.
-}

myStartupHook        = do
  startupHook defaultConfig
  spawn "compton -cfF -t-9 -l-11 -r9 -o.95 -D6 &"
  setWMName "LG3D"
-- }}}

-- MAIN {{{
main = do
    xmproc <- spawnPipe "xmobar"
    xmonad $ ewmh $ docks myBaseConfig
        { manageHook = myManageHook
          , layoutHook = myLayoutHook
          , borderWidth = 3
          , startupHook = myStartupHook
          , workspaces = myWorkspaces
          , modMask = myModMask
          , logHook = myLogHook xmproc
          , keys = myKeys
          , terminal = myTerminal
        }
-- }}}
