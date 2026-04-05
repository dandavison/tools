use std::fmt::Write;
use std::io::Read;

const COLORS_16: [&str; 16] = [
    "#000000", "#aa0000", "#00aa00", "#aa5500", "#0000aa", "#aa00aa", "#00aaaa", "#aaaaaa",
    "#555555", "#ff5555", "#55ff55", "#ffff55", "#5555ff", "#ff55ff", "#55ffff", "#ffffff",
];

fn color_256(n: u8) -> String {
    if n < 16 {
        return COLORS_16[n as usize].to_string();
    }
    if n < 232 {
        let n = n - 16;
        let r = (n / 36) as u32 * 51;
        let g = ((n % 36) / 6) as u32 * 51;
        let b = (n % 6) as u32 * 51;
        return format!("#{r:02x}{g:02x}{b:02x}");
    }
    let g = 8 + (n as u32 - 232) * 10;
    format!("#{g:02x}{g:02x}{g:02x}")
}

#[derive(Default)]
struct SgrState {
    fg: Option<String>,
    bg: Option<String>,
    bold: bool,
    italic: bool,
    underline: bool,
    strikethrough: bool,
}

impl SgrState {
    fn clear(&mut self) {
        *self = Self::default();
    }

    fn to_style(&self) -> String {
        let mut parts = Vec::new();
        if let Some(fg) = &self.fg {
            parts.push(format!("color:{fg}"));
        }
        if let Some(bg) = &self.bg {
            parts.push(format!("background-color:{bg}"));
        }
        if self.bold {
            parts.push("font-weight:bold".into());
        }
        if self.italic {
            parts.push("font-style:italic".into());
        }
        let mut decorations = Vec::new();
        if self.underline {
            decorations.push("underline");
        }
        if self.strikethrough {
            decorations.push("line-through");
        }
        if !decorations.is_empty() {
            parts.push(format!("text-decoration:{}", decorations.join(" ")));
        }
        parts.join(";")
    }

    fn parse(&mut self, params: &[u32]) {
        let mut i = 0;
        while i < params.len() {
            match params[i] {
                0 => self.clear(),
                1 => self.bold = true,
                3 => self.italic = true,
                4 => self.underline = true,
                9 => self.strikethrough = true,
                22 => self.bold = false,
                23 => self.italic = false,
                24 => self.underline = false,
                29 => self.strikethrough = false,
                p @ 30..=37 => self.fg = Some(COLORS_16[(p - 30) as usize].into()),
                38 => {
                    if let Some(&[5, n]) = params.get(i + 1..i + 3) {
                        self.fg = Some(color_256(n as u8));
                        i += 2;
                    } else if let Some(&[2, r, g, b]) = params.get(i + 1..i + 5) {
                        self.fg = Some(format!("#{r:02x}{g:02x}{b:02x}"));
                        i += 4;
                    }
                }
                39 => self.fg = None,
                p @ 40..=47 => self.bg = Some(COLORS_16[(p - 40) as usize].into()),
                48 => {
                    if let Some(&[5, n]) = params.get(i + 1..i + 3) {
                        self.bg = Some(color_256(n as u8));
                        i += 2;
                    } else if let Some(&[2, r, g, b]) = params.get(i + 1..i + 5) {
                        self.bg = Some(format!("#{r:02x}{g:02x}{b:02x}"));
                        i += 4;
                    }
                }
                49 => self.bg = None,
                p @ 90..=97 => self.fg = Some(COLORS_16[(p - 90 + 8) as usize].into()),
                p @ 100..=107 => self.bg = Some(COLORS_16[(p - 100 + 8) as usize].into()),
                _ => {}
            }
            i += 1;
        }
    }
}

fn html_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            _ => out.push(c),
        }
    }
    out
}

fn parse_osc8(seq: &str) -> Option<&str> {
    let inner = seq.strip_prefix("\x1b]8;")?;
    let inner = inner
        .strip_suffix("\x1b\\")
        .or_else(|| inner.strip_suffix('\x07'))?;
    let (_params, url) = inner.split_once(';')?;
    Some(url)
}

enum Token<'a> {
    Text(&'a str),
    Osc8(&'a str),
    Sgr(&'a str),
    Csi,
}

fn tokenize(input: &str) -> Vec<Token<'_>> {
    let mut tokens = Vec::new();
    let bytes = input.as_bytes();
    let mut pos = 0;
    let mut text_start = 0;

    while pos < bytes.len() {
        if bytes[pos] == 0x1b {
            if bytes.get(pos + 1) == Some(&b']')
                && bytes.get(pos + 2) == Some(&b'8')
                && bytes.get(pos + 3) == Some(&b';')
            {
                if text_start < pos {
                    tokens.push(Token::Text(&input[text_start..pos]));
                }
                let start = pos;
                pos += 4;
                while pos < bytes.len() {
                    if bytes[pos] == 0x1b && bytes.get(pos + 1) == Some(&b'\\') {
                        pos += 2;
                        break;
                    }
                    if bytes[pos] == 0x07 {
                        pos += 1;
                        break;
                    }
                    pos += 1;
                }
                tokens.push(Token::Osc8(&input[start..pos]));
                text_start = pos;
                continue;
            }
            if bytes.get(pos + 1) == Some(&b'[') {
                if text_start < pos {
                    tokens.push(Token::Text(&input[text_start..pos]));
                }
                let start = pos;
                pos += 2;
                while pos < bytes.len() && (0x30..=0x3f).contains(&bytes[pos]) {
                    pos += 1;
                }
                if pos < bytes.len() && (0x40..=0x7e).contains(&bytes[pos]) {
                    let final_byte = bytes[pos];
                    pos += 1;
                    if final_byte == b'm' {
                        tokens.push(Token::Sgr(&input[start..pos]));
                    } else {
                        tokens.push(Token::Csi);
                    }
                }
                text_start = pos;
                continue;
            }
        }
        pos += 1;
    }
    if text_start < bytes.len() {
        tokens.push(Token::Text(&input[text_start..]));
    }
    tokens
}

fn convert(input: &str) -> String {
    let tokens = tokenize(input);
    let mut out = String::with_capacity(input.len());
    let mut state = SgrState::default();
    let mut span_open = false;
    let mut link_open = false;

    for token in &tokens {
        match token {
            Token::Text(s) => out.push_str(&html_escape(s)),
            Token::Csi => {}
            Token::Osc8(seq) => {
                if let Some(url) = parse_osc8(seq) {
                    if url.is_empty() {
                        if link_open {
                            out.push_str("</a>");
                            link_open = false;
                        }
                    } else {
                        if link_open {
                            out.push_str("</a>");
                        }
                        let _ = write!(out, "<a href=\"{}\">", html_escape(url));
                        link_open = true;
                    }
                }
            }
            Token::Sgr(seq) => {
                let params_str = &seq[2..seq.len() - 1];
                let params: Vec<u32> = params_str
                    .split(';')
                    .map(|s| s.parse().unwrap_or(0))
                    .collect();
                if span_open {
                    out.push_str("</span>");
                    span_open = false;
                }
                state.parse(&params);
                let style = state.to_style();
                if !style.is_empty() {
                    let _ = write!(out, "<span style=\"{style}\">");
                    span_open = true;
                }
            }
        }
    }
    if span_open {
        out.push_str("</span>");
    }
    if link_open {
        out.push_str("</a>");
    }
    out
}

fn main() {
    let dark = std::env::args().any(|a| a == "--dark");
    let (bg, fg) = if dark {
        ("#0d1117", "#c9d1d9")
    } else {
        ("#ffffff", "#24292f")
    };

    let mut raw = String::new();
    std::io::stdin().read_to_string(&mut raw).unwrap();
    let body = convert(&raw);

    print!(
        r#"<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
  background: {bg};
  color: {fg};
  margin: 0;
  padding: 16px;
}}
pre {{
  font-family: "JetBrains Mono", "Fira Code", "SF Mono", Menlo, monospace;
  font-size: 13px;
  line-height: normal;
  white-space: pre-wrap;
  word-wrap: break-word;
}}
a {{
  color: inherit;
  text-decoration: none;
}}
</style>
</head>
<body>
<pre>{body}</pre>
</body>
</html>"#
    );
}
