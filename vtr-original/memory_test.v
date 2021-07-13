module test_memory (input clk,
             input             sel,
             input             we, 
             input [SIZE-1:0]  adr, 
             input [WIDTH-1:0]      dat_i, 
             output reg [WIDTH-1:0] dat_o);
   parameter  SIZE = 16; // Address size
   parameter WIDTH = 256;

   reg [WIDTH-1:0] mem [0:(1 << SIZE)-1];
   integer    i;

   initial begin
      for (i = 0; i < (1<<SIZE) - 1; i = i + 1)
        mem[i] <= 0;
   end
   
   always @(posedge clk)
     if (sel & ~we)
       dat_o <= mem[adr];

   always @(posedge clk)
     if (sel & we)
       mem[adr] <= dat_i;
endmodule