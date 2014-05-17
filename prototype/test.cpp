
#include <string>
#include <vector>
#include <iostream>
#include <boost/shared_ptr.hpp>
#include <boost/optional/optional.hpp>

//using namespace std;
//string susing("kartupelis");


static double d; // 8
static double dx10[10];
static union {
        double d;
        struct {
                float f1, f2;
        } fs;
} u; // 8

// Let's assume string is pointer+size+data.
static std::string s0; // ~16
static std::string s10("kartupelis"); // ~26
static std::string s0x10[10]; // ~160
static std::string s10x10[10] = { std::string("kartupelis"), std::string("kartupelis"), std::string("kartupelis"), std::string("kartupelis"), std::string("kartupelis"), std::string("kartupelis"), std::string
("kartupelis"), std::string("kartupelis"), std::string("kartupelis"), std::string("kartupelis") }; // ~260

static std::ios_base* p = &std::cout; // ~8
static std::ios_base& r = std::cout; // ~8

static std::string& s10r = s10;

// Let's assume vector is pointer+size+data.
std::vector<std::string> vs; // ~51
std::vector<double> vd; // ~8016
std::vector<double> vde; // ~16

class Base {
public:
        virtual ~Base() {}
};

class Derived: public Base {
public:
        Derived(): field(1000, 'a') {}
        virtual ~Derived() {}
private:
        std::string field;
};

// Let's assume smart_ptr is pointer+refcount, split the content size.
static boost::shared_ptr< std::string > s1, s2, s3, s4; // ~250 each
boost::shared_ptr<Base> sb ( new Derived ); // ~1032

// Let's assume boost::optional keeps a reserved space for the value it contains + 4 byte bool.
static boost::optional< Derived > o; // ~36
static boost::optional< Derived > od = Derived(); // ~1020
static boost::optional< const char& > oc('c'); // ~13

struct anon
{
        void* v1;
        struct {
                void* v2;
        };
        struct {
                void* v3;
        };
        struct {
                const char* c; // "suns"
        };
} a; // 32

void (*fp)(void); // 8

typedef int my_int;

//typedef boost::shared_ptr<Derived> (*tf)(boost::shared_ptr<Derived>, std::string);
//static const tf fff = 0;

template <typename T>
struct templ {
        T x;
        std::string s;
        std::vector<T> xv;
        boost::shared_ptr<Derived> (*inner)(boost::shared_ptr<Derived>, std::string);
};
struct evil {
        struct {
                templ< boost::shared_ptr<Derived> (*)(boost::shared_ptr<Derived>, std::string) > inner;
        } x;
} evilvar; // 4

class Base2
{
        int i;
};
class Derived2: private Base2
{
}; // 4
Derived2 d2;

class DestroyAlignment: Derived2
{
        int j;
}; // 8
DestroyAlignment di;

class Empty
{
}; // 1
Empty e;

struct EnumStruct
{
        enum Enum {
                ONE,
                TWO
        } e;
} es; // 4

class Bitfields
{
        short b_0_3 : 3;
        short b_3_1 : 1;
        short : 0; // +2
        short b_16_1: 1; // +2
} bf; // 4

class BigChar
{
        char x : 80;
        char : 80;
} bc; // 20 (but I see GCC aligns them both up to 8 bytes, so I get 16+16 instead of 10+10)

class Static
{
        public: static int si; //TODO: find
};
int Static::si;

int g()
{
	// !!! Not only can't I find function static variables, I can't find them by name either. I can
	// use 'info variables' to get the names and addresses but there are no types, so I can't cast
	// the addresses to the types either. There is more info in the 'maint *' commands of evilness but
	// using them seems too wrong.
	//
	// (gdb) p g()
	// $7 = 13
	// (gdb) p g::static_in_g
	// No symbol "static_in_g" in specified context.
	// (gdb) p 'g()'::static_in_g
	// No symbol "static_in_g" in specified context.
	// (gdb) p 'g()'::'static_in_g'
	// No symbol "static_in_g" in specified context.
	// (gdb) p g()::static_in_g
	// A syntax error in expression, near `static_in_g'.
	//
        static int static_in_g = 11; //TODO: find
	static struct lostruct { static int lostruct_s; int lostruct_v; } lostruct_var; //TODO: find?
        return static_in_g++;
}

void st();

void f()
{
        int hmm; // 4
        static volatile int i = 0; // 4
	st();
        i++;
        static int j = 10; // 4
        breakpoint_here:
        i++; // need something to tell GCC that label is before block ends...
}


int main()
{
        s4 = s3 = s2 = s1 = boost::shared_ptr< std::string >( new std::string(1000, 'c') );
        vs.push_back("a");
        vs.push_back("bc");
        vd.reserve(1000);
        vd.push_back(1);
        a.c = "suns";
	Static::si = 8;
        int var_in_main = 5;
	struct {
		static int mss; //TODO: find?
	} ms;
        static int static_in_main = 4;
        {
                int var_in_main_2 = 8;
                g();
                f();
        }
}

