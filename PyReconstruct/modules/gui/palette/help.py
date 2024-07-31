palette_help = """Traces created in the field take on the attributes of the currently selected palette button.
<br><br>
<b>Right-click</b> on a button to edit its attributes.
<br><br>
<b>Left-click</b> on button to use its attributes when tracing.
<br><br>
Alternatively, you can edit all palette options by clicking on the ☰ icon next to the palette.
<br><br>
Note that whitespace and commas are not allowed in trace names and will be replaced with
underscores.
<br>
<hr>
<br>
<center><b>Special Characters</b></center>
<br><br>
<b>Angle brackets &lt; &gt;</b>
<br><br>
Any number bounded by angle brackets (&lt;1&gt;, &lt;01&gt;, &lt;001&gt;, &lt;053&gt;, etc.) is incremented
each time you create a new trace in the field. The backets are not included in the trace name.
<br><br>
Example: "thing_&lt;01&gt;"
<br><br>
The first trace created in the field is named "thing_01", the next "thing_02", and so on.
<br><br>
<b>Curly brackets { }</b>
<br><br>
Numbers inside curly brackets are incremented when you press the "+" or "-"
buttons. The brackets are not included in the trace name.
<br><br>
When the "⚭" button is selected, all traces with numbers inside curly brackets will be incremented.
<br><br>
When the "⚬" button is selected, only the active trace will be incremented.
<br><br>
<b>Example:</b> "thing_{01}" and "thing_{01}_feature"
<br><br>
With "thing_{01}" active, when the user presses "+":
<br><br>
if "⚭" selected: these buttons will now correspond to "thing_02" and "thing_02_feature".
<br><br>
if "⚬" selected: the buttons will now correspond to "thing_02" and "thing_01_feature".
"""
