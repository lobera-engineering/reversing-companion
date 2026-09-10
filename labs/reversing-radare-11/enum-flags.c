#include <stdio.h>

enum designFlags {
	BOLD = 1,
	ITALICS = 2,
	UNDERLINE = 4
};

int main() {
	int myDesign = BOLD | UNDERLINE; 

        //    
        //  | 
        //  ___________
        //    

	printf("%d", myDesign);

	return 0;
}
