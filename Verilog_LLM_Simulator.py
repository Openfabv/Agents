!pip install -q transformers torch accelerate bitsandbytes
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# Load model in 4-bit quantization to fit GPU memory
model_id = "Qwen/Qwen2.5-Coder-7B-Instruct"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto"
)

prompt = """
Write a synthesizable Verilog module for a 4-bit up-counter with clk, active-low rst_n, and count output.
Only return raw Verilog code inside ```verilog ... ``` codeblock.
"""

messages = [
    {"role": "system", "content": "You are an expert ASIC digital design engineer writing clean Verilog 2001 code."},
    {"role": "user", "content": prompt}
]

text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer([text], return_tensors="pt").to("cuda")

outputs = model.generate(**inputs, max_new_tokens=400)
response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

# Extract Verilog code from the response
import re
verilog_code_match = re.search(r"```verilog\n(.*?)```", response, re.DOTALL)

if verilog_code_match:
    verilog_code = verilog_code_match.group(1).strip()
    with open("counter.v", "w") as f:
        f.write(verilog_code)
    print("Verilog code saved to counter.v")
    print("\nContent of counter.v:\n")
    with open("counter.v", "r") as f:
        print(f.read())
else:
    print("No Verilog code block found in the response.")

testbench_code = """
`timescale 1ns / 1ps

module counter_tb;

  // Testbench signals
  reg clk;
  reg rst_n;
  wire [3:0] count;

  // Instantiate the Device Under Test (DUT)
  four_bit_up_counter dut (
    .clk(clk),
    .rst_n(rst_n),
    .count(count)
  );

  // Clock generation
  initial begin
    clk = 0;
    forever #5 clk = ~clk; // 10ns period (100 MHz clock)
  end

  // Reset and test sequence
  initial begin
    // Initialize inputs
    rst_n = 0; // Assert reset
    #10 rst_n = 1; // Deassert reset after 10ns

    // Monitor and display signals
    $monitor("Time=%0t | rst_n=%b | clk=%b | count=%d", $time, rst_n, clk, count);

    // Dump waveforms for debugging (optional)
    $dumpfile("counter_tb.vcd");
    $dumpvars(0, counter_tb);

    // Run simulation for a period and then terminate
    #100 $finish;
  end

endmodule
"""

with open("counter_tb.v", "w") as f:
    f.write(testbench_code)

print("Testbench code saved to counter_tb.v")
print("\nContent of counter_tb.v:\n")
with open("counter_tb.v", "r") as f:
    print(f.read())

!iverilog -o counter_sim counter.v counter_tb.v
!vvp counter_sim


print("Generated Output:\n", response)
