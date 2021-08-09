// `define RAMWIDTH 12'b010000000000
// `define rRAMSIZEWIDTH 7

module dual_port_ram
#(
	parameter RAMSIZEWIDTH = 8,
	parameter RAMWIDTH = 8
)
(
	input clk, we1, we2,
	input [RAMWIDTH-1:0] data1, data2,
	input [RAMSIZEWIDTH-1:0] addr1, addr2,
	output reg [RAMWIDTH-1:0]  out1, out2

	// input [7:0] data_a, data_b,
	// input [5:0] addr_a, addr_b,
	// input we_a, we_b, clk,
	// output reg [7:0] q_a, q_b
);
	// Declare the RAM variable
	reg [RAMWIDTH-1 : 0] ram [RAMSIZEWIDTH-1 :0];
	
	// Port A
	always @ (posedge clk)
	begin
		if (we1) 
		begin
			ram[addr1] <= data1;
			out1 <= data1;
		end
		else 
		begin
			out1 <= ram[addr1];
		end
	end
	
	// Port B
	always @ (posedge clk)
	begin
		if (we2)
		begin
			ram[addr2] <= data2;
			out2 <= data2;
		end
		else
		begin
			out2 <= ram[addr2];
		end
	end
	
endmodule
